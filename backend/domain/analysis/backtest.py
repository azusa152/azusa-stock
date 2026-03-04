"""
Domain — Backtesting pure calculation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from statistics import median
from typing import TYPE_CHECKING

from domain.constants import (
    BACKTEST_FP_WINDOW,
    BACKTEST_MIN_SAMPLES_HIGH,
    BACKTEST_MIN_SAMPLES_MEDIUM,
    BACKTEST_WINDOWS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class BacktestSignalEvent:
    """Minimal signal event payload for backtesting calculations."""

    ticker: str
    signal: str
    market_status: str
    scanned_at: datetime


SIGNAL_DIRECTION: dict[str, str] = {
    "DEEP_VALUE": "buy",
    "OVERSOLD": "buy",
    "CONTRARIAN_BUY": "buy",
    "APPROACHING_BUY": "buy",
    "THESIS_BROKEN": "sell",
    "OVERHEATED": "sell",
    "CAUTION_HIGH": "sell",
    "WEAKENING": "sell",
}


def deduplicate_signal_events(
    logs: Sequence[BacktestSignalEvent],
) -> list[BacktestSignalEvent]:
    """
    Collapse consecutive identical signals per ticker into one transition event.

    The input must be sorted by (ticker, scanned_at asc) or at least scanned_at asc
    within each ticker.
    """
    deduped: list[BacktestSignalEvent] = []
    last_signal_by_ticker: dict[str, str] = {}

    for event in logs:
        previous_signal = last_signal_by_ticker.get(event.ticker)
        if previous_signal != event.signal:
            deduped.append(event)
            last_signal_by_ticker[event.ticker] = event.signal

    return deduped


def _price_date(price_point: dict) -> date:
    return date.fromisoformat(str(price_point["date"]))


def _price_close(price_point: dict) -> float:
    return float(price_point["close"])


def _find_start_index(signal_date: date, sorted_prices: Sequence[dict]) -> int | None:
    """
    Find the first trading day index on/after signal_date.
    """
    for idx, point in enumerate(sorted_prices):
        if _price_date(point) >= signal_date:
            return idx
    return None


def compute_forward_returns(
    signal_date: date,
    price_series: Sequence[dict],
    windows: Sequence[int] | None = None,
    already_sorted: bool = False,
) -> dict[int, float | None]:
    """
    Compute forward returns by trading-day index (not calendar days).
    """
    target_windows = list(windows or BACKTEST_WINDOWS)
    if not price_series:
        return dict.fromkeys(target_windows)

    sorted_prices = (
        price_series if already_sorted else sorted(price_series, key=_price_date)
    )
    start_idx = _find_start_index(signal_date, sorted_prices)
    if start_idx is None:
        return dict.fromkeys(target_windows)

    entry_price = _price_close(sorted_prices[start_idx])
    if entry_price <= 0:
        return dict.fromkeys(target_windows)

    returns: dict[int, float | None] = {}
    for window in target_windows:
        exit_idx = start_idx + window
        if exit_idx >= len(sorted_prices):
            returns[window] = None
            continue
        exit_price = _price_close(sorted_prices[exit_idx])
        if exit_price <= 0:
            returns[window] = None
            continue
        returns[window] = round((exit_price / entry_price - 1) * 100, 4)
    return returns


def classify_confidence(sample_count: int) -> str:
    if sample_count >= BACKTEST_MIN_SAMPLES_HIGH:
        return "high"
    if sample_count >= BACKTEST_MIN_SAMPLES_MEDIUM:
        return "medium"
    return "low"


def _is_hit(signal_type: str, return_pct: float) -> bool:
    """A flat (0%) return is conservatively treated as a miss for both directions."""
    direction = SIGNAL_DIRECTION.get(signal_type, "buy")
    if direction == "sell":
        return return_pct < 0
    return return_pct > 0


def compute_signal_metrics(
    forward_returns: Sequence[dict[int, float | None]],
    signal_type: str,
) -> dict:
    """
    Aggregate backtest metrics per window for a single signal type.
    """
    windows = sorted(
        set(BACKTEST_WINDOWS) | {window for item in forward_returns for window in item}
    )
    window_metrics: list[dict] = []

    for window in windows:
        values: list[float] = [
            float(item[window])
            for item in forward_returns
            if window in item and item[window] is not None
        ]
        sample_count = len(values)
        if sample_count == 0:
            window_metrics.append(
                {
                    "window_days": window,
                    "hit_rate": 0.0,
                    "avg_return_pct": 0.0,
                    "median_return_pct": 0.0,
                    "sample_count": 0,
                }
            )
            continue

        hits = sum(1 for value in values if _is_hit(signal_type, value))
        window_metrics.append(
            {
                "window_days": window,
                "hit_rate": round(hits / sample_count, 4),
                "avg_return_pct": round(sum(values) / sample_count, 4),
                "median_return_pct": round(float(median(values)), 4),
                "sample_count": sample_count,
            }
        )

    fp_values: list[float] = [
        float(item[BACKTEST_FP_WINDOW])
        for item in forward_returns
        if BACKTEST_FP_WINDOW in item and item[BACKTEST_FP_WINDOW] is not None
    ]
    fp_sample_count = len(fp_values)
    if fp_sample_count == 0:
        false_positive_rate = 0.0
    else:
        hits = sum(1 for value in fp_values if _is_hit(signal_type, value))
        false_positive_rate = round(1 - hits / fp_sample_count, 4)

    return {
        "signal": signal_type,
        "direction": SIGNAL_DIRECTION.get(signal_type, "buy"),
        "total_occurrences": len(forward_returns),
        "confidence": classify_confidence(len(forward_returns)),
        "windows": window_metrics,
        "false_positive_rate": false_positive_rate,
    }
