# pyright: reportCallIssue=false
"""
Application — Signal backtesting service orchestration.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from domain.analysis import (
    BacktestSignalEvent,
    compute_forward_returns,
    compute_signal_metrics,
    deduplicate_signal_events,
)
from domain.constants import BACKTEST_CACHE_TTL, BACKTEST_MAX_LOOKBACK_DAYS
from infrastructure import repositories as repo
from infrastructure.market_data import get_price_history
from logging_config import get_logger

if TYPE_CHECKING:
    from sqlmodel import Session

logger = get_logger(__name__)

_backtest_cache_lock = threading.Lock()
_backtest_cache: dict[str, Any] = {}
_backtest_cache_ts = 0.0


def invalidate_backtest_cache() -> None:
    """Invalidate in-memory backtest cache."""
    global _backtest_cache, _backtest_cache_ts
    with _backtest_cache_lock:
        _backtest_cache = {}
        _backtest_cache_ts = 0.0


def _normalize_scan_time(scanned_at: datetime) -> datetime:
    if scanned_at.tzinfo is None:
        return scanned_at.replace(tzinfo=UTC)
    return scanned_at.astimezone(UTC)


def _to_events(logs: list) -> list[BacktestSignalEvent]:
    return [
        BacktestSignalEvent(
            ticker=log.stock_ticker,
            signal=log.signal,
            market_status=log.market_status,
            scanned_at=_normalize_scan_time(log.scanned_at),
        )
        for log in logs
    ]


def _build_payload(session: Session) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=BACKTEST_MAX_LOOKBACK_DAYS)
    raw_logs = repo.find_scan_logs_for_backtest(
        session, since=since, exclude_signals=None
    )
    events = deduplicate_signal_events(_to_events(raw_logs))

    logger.info("Backtest events: raw=%d deduped=%d", len(raw_logs), len(events))

    prices_by_ticker: dict[str, list[dict]] = {}
    returns_by_signal: dict[str, list[dict[int, float | None]]] = {}
    occurrences_by_signal: dict[str, list[dict[str, Any]]] = {}

    for event in events:
        if event.ticker not in prices_by_ticker:
            prices = get_price_history(event.ticker) or []
            prices_by_ticker[event.ticker] = sorted(
                prices,
                key=lambda point: str(point["date"]),
            )

        forward_returns = compute_forward_returns(
            signal_date=event.scanned_at.date(),
            price_series=prices_by_ticker[event.ticker],
            already_sorted=True,
        )
        returns_by_signal.setdefault(event.signal, []).append(forward_returns)
        occurrences_by_signal.setdefault(event.signal, []).append(
            {
                "ticker": event.ticker,
                "signal_date": event.scanned_at.date(),
                "market_status": event.market_status,
                "forward_returns": {f"{k}d": v for k, v in forward_returns.items()},
            }
        )

    summary_items: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    for signal, signal_returns in returns_by_signal.items():
        summary = compute_signal_metrics(signal_returns, signal)
        summary_items.append(summary)
        details[signal] = {
            "signal": signal,
            "direction": summary["direction"],
            "summary": summary,
            "occurrences": occurrences_by_signal.get(signal, []),
        }

    summary_items.sort(key=lambda item: item["signal"])
    computed_at = datetime.now(UTC)
    payload = {
        "summary": {
            "signals": summary_items,
            "lookback_days": BACKTEST_MAX_LOOKBACK_DAYS,
            "computed_at": computed_at,
            "total_signals_evaluated": len(events),
        },
        "details": details,
    }
    return payload


def _get_or_build_payload(session: Session) -> dict[str, Any]:
    global _backtest_cache, _backtest_cache_ts
    with _backtest_cache_lock:
        now = time.time()
        if _backtest_cache and now - _backtest_cache_ts < BACKTEST_CACHE_TTL:
            return _backtest_cache
        payload = _build_payload(session)
        _backtest_cache = payload
        _backtest_cache_ts = time.time()
        return payload


def get_backtest_summary(session: Session) -> dict[str, Any]:
    """Return signal-level backtest summary."""
    payload = _get_or_build_payload(session)
    return payload["summary"]


def get_backtest_detail(
    session: Session,
    signal_type: str,
    limit: int = 50,
) -> dict[str, Any] | None:
    """Return detailed occurrences for a single signal type."""
    payload = _get_or_build_payload(session)
    detail = payload["details"].get(signal_type)
    if not detail:
        return None

    occurrences = detail.get("occurrences", [])
    safe_limit = max(1, limit)
    return {
        **detail,
        "total_occurrences": len(occurrences),
        "occurrences": occurrences[:safe_limit],
    }
