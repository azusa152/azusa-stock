"""
Application — ScanLog cold-start backfill service.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, time

from sqlmodel import Session, select

from application.scan.backtest_service import invalidate_backtest_cache
from domain.analysis import replay_historical_signals
from domain.constants import (
    BACKFILL_HISTORY_PERIOD,
    BACKFILL_MARKET_STATUS,
    BACKFILL_MIN_HISTORY_DAYS,
    BACKFILL_SAMPLE_INTERVAL,
    SKIP_SIGNALS_CATEGORIES,
)
from domain.entities import ScanLog
from infrastructure import repositories as repo
from infrastructure.market_data import batch_download_history_extended
from logging_config import get_logger

logger = get_logger(__name__)

_backfill_lock = threading.Lock()
_backfill_in_progress = False
_backfill_total = 0
_backfill_completed = 0


def _set_progress(
    *, in_progress: bool, total: int | None = None, completed: int | None = None
) -> None:
    global _backfill_in_progress, _backfill_total, _backfill_completed
    with _backfill_lock:
        _backfill_in_progress = in_progress
        if total is not None:
            _backfill_total = total
        if completed is not None:
            _backfill_completed = completed


def _increment_completed() -> None:
    global _backfill_completed
    with _backfill_lock:
        _backfill_completed += 1


def get_backfill_status() -> dict[str, int | bool]:
    with _backfill_lock:
        return {
            "is_backfilling": _backfill_in_progress,
            "total": _backfill_total,
            "completed": _backfill_completed,
        }


def backfill_scan_logs(session: Session) -> int:
    """
    Backfill synthetic ScanLog rows by replaying historical signal events.
    """
    global _backfill_in_progress
    with _backfill_lock:
        if _backfill_in_progress:
            logger.info(
                "ScanLog backfill already in progress; skipping duplicate trigger."
            )
            return 0
        _backfill_in_progress = True

    inserted = 0
    try:
        stocks = [
            stock
            for stock in repo.find_active_stocks(session)
            if stock.category.value not in SKIP_SIGNALS_CATEGORIES
        ]
        if not stocks:
            logger.info("No eligible stocks for ScanLog backfill.")
            _set_progress(in_progress=False, total=0, completed=0)
            return 0

        existing_backfilled_tickers = set(
            session.exec(
                select(ScanLog.stock_ticker)
                .where(ScanLog.market_status == BACKFILL_MARKET_STATUS)
                .distinct()
            ).all()
        )
        pending_stocks = [
            stock for stock in stocks if stock.ticker not in existing_backfilled_tickers
        ]
        already_completed = len(stocks) - len(pending_stocks)
        _set_progress(
            in_progress=True,
            total=len(stocks),
            completed=already_completed,
        )
        if not pending_stocks:
            logger.info("ScanLog backfill already complete for all eligible stocks.")
            _set_progress(
                in_progress=False,
                total=len(stocks),
                completed=len(stocks),
            )
            return 0

        tickers = [stock.ticker for stock in pending_stocks]
        history_map = batch_download_history_extended(
            tickers=tickers,
            period=BACKFILL_HISTORY_PERIOD,
            min_days=BACKFILL_MIN_HISTORY_DAYS,
        )

        for stock in pending_stocks:
            prices = history_map.get(stock.ticker)
            if not prices:
                _increment_completed()
                continue

            try:
                events = replay_historical_signals(
                    price_series=prices,
                    category=stock.category.value,
                    sample_interval=BACKFILL_SAMPLE_INTERVAL,
                    include_normal=True,
                )
                previous_signal: str | None = None
                for signal_date, signal in events:
                    if signal == previous_signal:
                        continue
                    previous_signal = signal
                    if signal == "NORMAL":
                        continue
                    repo.create_scan_log(
                        session,
                        ScanLog(
                            stock_ticker=stock.ticker,
                            signal=signal,
                            market_status=BACKFILL_MARKET_STATUS,
                            scanned_at=datetime.combine(
                                signal_date, time.min, tzinfo=UTC
                            ),
                        ),
                    )
                    inserted += 1
                session.commit()
            except Exception as exc:
                session.rollback()
                logger.warning("ScanLog backfill failed for %s: %s", stock.ticker, exc)
            finally:
                _increment_completed()

        invalidate_backtest_cache()
        logger.info("ScanLog backfill finished. inserted=%d", inserted)
        return inserted
    finally:
        _set_progress(in_progress=False)
