"""
Application — Guru clone-portfolio backtest service.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import yfinance as yf

from domain.analysis import HoldingSnapshot, QuarterInput, compute_clone_returns
from domain.constants import GURU_BACKTEST_CACHE_TTL, GURU_BACKTEST_MAX_QUARTERS
from domain.enums import HoldingAction
from i18n import t
from infrastructure.repositories import (
    find_filings_by_guru,
    find_guru_by_id,
    find_holdings_by_filing,
)
from logging_config import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from sqlmodel import Session

_guru_backtest_cache_lock = threading.Lock()
_guru_backtest_cache: dict[str, Any] = {}
_guru_backtest_cache_ts: dict[str, float] = {}

_SUPPORTED_BENCHMARKS: set[str] = {"SPY", "VT"}


def invalidate_guru_backtest_cache() -> None:
    """Invalidate in-memory guru backtest cache."""
    global _guru_backtest_cache, _guru_backtest_cache_ts
    with _guru_backtest_cache_lock:
        _guru_backtest_cache = {}
        _guru_backtest_cache_ts = {}


def get_guru_backtest(
    session: Session,
    guru_id: int,
    quarters: int,
    benchmark: str,
    lang: str = "zh-TW",
) -> dict | None:
    """Get guru clone-portfolio backtest payload with TTL cache."""
    normalized_benchmark = benchmark.upper()
    normalized_quarters = max(2, min(quarters, GURU_BACKTEST_MAX_QUARTERS))
    cache_key = f"guru:{guru_id}:q:{normalized_quarters}:bm:{normalized_benchmark}"

    with _guru_backtest_cache_lock:
        now = time.time()
        ts = _guru_backtest_cache_ts.get(cache_key, 0.0)
        cached = _guru_backtest_cache.get(cache_key)
        if cached is not None and now - ts < GURU_BACKTEST_CACHE_TTL:
            return cached

    payload = _build_guru_backtest_payload(
        session=session,
        guru_id=guru_id,
        quarters=normalized_quarters,
        benchmark=normalized_benchmark,
        lang=lang,
    )
    if payload is None:
        return None

    with _guru_backtest_cache_lock:
        _guru_backtest_cache[cache_key] = payload
        _guru_backtest_cache_ts[cache_key] = time.time()
    return payload


def _build_guru_backtest_payload(
    session: Session,
    guru_id: int,
    quarters: int,
    benchmark: str,
    lang: str,
) -> dict | None:
    guru = find_guru_by_id(session, guru_id)
    if guru is None:
        return None

    if benchmark not in _SUPPORTED_BENCHMARKS:
        logger.warning(
            "Unsupported benchmark '%s', fallback to SPY for guru_id=%s",
            benchmark,
            guru_id,
        )
        benchmark = "SPY"

    filings_desc = find_filings_by_guru(
        session, guru_id, limit=GURU_BACKTEST_MAX_QUARTERS + 1
    )
    if len(filings_desc) < 2:
        raise ValueError("not_enough_filings")

    filings_asc = sorted(filings_desc, key=lambda filing: filing.filing_date)
    selected_filings = filings_asc[-quarters:]

    quarter_inputs: list[QuarterInput] = []
    top5_by_filing_date: dict[str, list[str]] = {}
    ticker_set: set[str] = set()

    for filing in selected_filings:
        holdings = find_holdings_by_filing(session, filing.id)
        eligible = [
            holding
            for holding in holdings
            if holding.ticker
            and holding.action != HoldingAction.SOLD_OUT.value
            and (holding.weight_pct or 0) > 0
        ]
        eligible_sorted = sorted(
            eligible,
            key=lambda holding: holding.weight_pct or 0.0,
            reverse=True,
        )
        top5_by_filing_date[filing.filing_date] = [
            holding.ticker for holding in eligible_sorted[:5] if holding.ticker
        ]

        snapshots = [
            HoldingSnapshot(
                ticker=holding.ticker or "", weight_pct=holding.weight_pct or 0.0
            )
            for holding in eligible_sorted
            if holding.ticker
        ]
        if snapshots:
            quarter_inputs.append(
                QuarterInput(
                    report_date=filing.report_date,
                    filing_date=filing.filing_date,
                    holdings=snapshots,
                )
            )
            ticker_set.update(snapshot.ticker for snapshot in snapshots)

    if len(quarter_inputs) < 2:
        raise ValueError("not_enough_filings")

    price_data, benchmark_prices = _download_price_history(
        tickers=sorted(ticker_set),
        benchmark=benchmark,
        start_date=date.fromisoformat(quarter_inputs[0].filing_date)
        - timedelta(days=7),
        end_date=date.today(),
    )

    if not benchmark_prices:
        raise ValueError("benchmark_data_missing")

    result = compute_clone_returns(
        quarter_inputs=quarter_inputs,
        price_data=price_data,
        benchmark_prices=benchmark_prices,
    )

    quarter_rows = []
    for quarter in result["quarters"]:
        filing_date = quarter["filing_date"]
        quarter_rows.append(
            {
                **quarter,
                "top5_holdings": top5_by_filing_date.get(filing_date, []),
            }
        )

    return {
        "guru_id": guru.id,
        "guru_display_name": guru.display_name,
        "benchmark": benchmark,
        "quarters": quarter_rows,
        "cumulative_series": result["cumulative_series"],
        "cumulative_clone_return": result["cumulative_clone_return"],
        "cumulative_benchmark_return": result["cumulative_benchmark_return"],
        "alpha": result["alpha"],
        "computed_at": datetime.now(UTC).isoformat(),
        "disclaimer": t("guru.backtest_disclaimer", lang=lang),
    }


def _download_price_history(
    tickers: list[str],
    benchmark: str,
    start_date: date,
    end_date: date,
) -> tuple[dict[str, list[dict]], list[dict]]:
    all_tickers = [*tickers, benchmark]
    unique_tickers = sorted({ticker for ticker in all_tickers if ticker})
    if not unique_tickers:
        return {}, []

    try:
        history_df = yf.download(
            unique_tickers,
            start=start_date,
            end=end_date + timedelta(days=1),
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=True,
        )
    except Exception as exc:
        logger.warning("Guru backtest 批次下載歷史價格失敗：%s", exc)
        return {}, []

    series_map: dict[str, list[dict]] = {}
    for ticker in unique_tickers:
        series_map[ticker] = _extract_close_series(history_df, ticker)

    return (
        {
            ticker: series
            for ticker, series in series_map.items()
            if ticker != benchmark
        },
        series_map.get(benchmark, []),
    )


def _extract_close_series(history_df: Any, ticker: str) -> list[dict]:
    try:
        frame = history_df[ticker]
    except (KeyError, TypeError):
        frame = history_df
    except Exception:
        return []

    if frame is None or getattr(frame, "empty", True):
        return []

    close_series: Any
    if getattr(frame, "ndim", 0) == 1:
        # Single-column selection can return Series depending on yfinance shape.
        close_series = frame.dropna()
    else:
        if "Close" not in frame:
            return []
        close_series = frame["Close"].dropna()

    rows: list[dict] = []
    for idx, value in close_series.items():
        try:
            rows.append(
                {
                    "date": idx.date().isoformat(),
                    "close": round(float(value), 6),
                }
            )
        except Exception:
            continue
    rows.sort(key=lambda row: row["date"])
    return rows
