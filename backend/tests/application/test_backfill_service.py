from datetime import date
from unittest.mock import patch

from sqlmodel import select

from application.scan.backfill_service import backfill_scan_logs, get_backfill_status
from domain.constants import BACKFILL_MARKET_STATUS
from domain.entities import ScanLog, Stock
from domain.enums import StockCategory


def _seed_stock(db_session, ticker: str, category: StockCategory) -> None:
    db_session.add(Stock(ticker=ticker, category=category, current_thesis="test"))
    db_session.commit()


def test_backfill_scan_logs_should_skip_cash_and_be_idempotent(db_session) -> None:
    _seed_stock(db_session, "AAPL", StockCategory.GROWTH)
    _seed_stock(db_session, "USD", StockCategory.CASH)

    mock_prices = [{"date": "2025-01-01", "close": 100.0}] * 220
    mock_events = [(date(2025, 5, 1), "OVERSOLD"), (date(2025, 5, 8), "OVERHEATED")]

    with (
        patch(
            "application.scan.backfill_service.batch_download_history_extended",
            return_value={"AAPL": mock_prices},
        ),
        patch(
            "application.scan.backfill_service.replay_historical_signals",
            return_value=mock_events,
        ) as mocked_replay,
    ):
        inserted_first = backfill_scan_logs(db_session)

    assert inserted_first == 2
    mocked_replay.assert_called_once()
    assert mocked_replay.call_args.kwargs["include_normal"] is True
    status = get_backfill_status()
    assert status["is_backfilling"] is False
    assert status["total"] == 1
    assert status["completed"] == 1

    rows = list(
        db_session.exec(
            select(ScanLog).where(ScanLog.market_status == BACKFILL_MARKET_STATUS)
        ).all()
    )
    assert len(rows) == 2
    assert all(row.stock_ticker == "AAPL" for row in rows)

    inserted_second = backfill_scan_logs(db_session)
    assert inserted_second == 0


def test_backfill_scan_logs_should_keep_signal_after_normal_reset(db_session) -> None:
    _seed_stock(db_session, "AAPL", StockCategory.GROWTH)

    mock_prices = [{"date": "2025-01-01", "close": 100.0}] * 220
    # A -> NORMAL -> A should keep both A events in backfill output.
    replay_events = [
        (date(2025, 5, 1), "OVERSOLD"),
        (date(2025, 5, 8), "NORMAL"),
        (date(2025, 5, 15), "OVERSOLD"),
    ]

    with (
        patch(
            "application.scan.backfill_service.batch_download_history_extended",
            return_value={"AAPL": mock_prices},
        ),
        patch(
            "application.scan.backfill_service.replay_historical_signals",
            return_value=replay_events,
        ),
    ):
        inserted = backfill_scan_logs(db_session)

    assert inserted == 2
    rows = list(
        db_session.exec(
            select(ScanLog)
            .where(ScanLog.market_status == BACKFILL_MARKET_STATUS)
            .order_by(ScanLog.scanned_at)
        ).all()
    )
    assert len(rows) == 2
    assert [row.signal for row in rows] == ["OVERSOLD", "OVERSOLD"]


def test_backfill_scan_logs_should_resume_only_missing_tickers(db_session) -> None:
    _seed_stock(db_session, "AAPL", StockCategory.GROWTH)
    _seed_stock(db_session, "MSFT", StockCategory.GROWTH)

    # Simulate an interrupted prior run that already backfilled AAPL.
    db_session.add(
        ScanLog(
            stock_ticker="AAPL",
            signal="OVERHEATED",
            market_status=BACKFILL_MARKET_STATUS,
        )
    )
    db_session.commit()

    mock_prices = [{"date": "2025-01-01", "close": 100.0}] * 220
    mock_events = [(date(2025, 5, 1), "OVERSOLD")]

    with (
        patch(
            "application.scan.backfill_service.batch_download_history_extended",
            return_value={"MSFT": mock_prices},
        ) as mocked_download,
        patch(
            "application.scan.backfill_service.replay_historical_signals",
            return_value=mock_events,
        ),
    ):
        inserted = backfill_scan_logs(db_session)

    assert inserted == 1
    mocked_download.assert_called_once()
    assert mocked_download.call_args.kwargs["tickers"] == ["MSFT"]
