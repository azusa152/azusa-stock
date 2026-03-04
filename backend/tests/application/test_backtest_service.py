from datetime import UTC, datetime
from unittest.mock import patch

from application.scan.backtest_service import (
    get_backtest_detail,
    get_backtest_summary,
    invalidate_backtest_cache,
)
from domain.entities import ScanLog, Stock
from domain.enums import StockCategory


def _seed_stock(db_session, ticker: str) -> None:
    db_session.add(
        Stock(ticker=ticker, category=StockCategory.GROWTH, current_thesis="test")
    )
    db_session.commit()


def test_get_backtest_summary_should_aggregate_and_deduplicate(db_session) -> None:
    _seed_stock(db_session, "AAPL")

    db_session.add_all(
        [
            ScanLog(
                stock_ticker="AAPL",
                signal="OVERSOLD",
                market_status="BULLISH",
                scanned_at=datetime(2026, 1, 2, tzinfo=UTC),
            ),
            ScanLog(  # same consecutive signal; should be deduplicated
                stock_ticker="AAPL",
                signal="OVERSOLD",
                market_status="BULLISH",
                scanned_at=datetime(2026, 1, 3, tzinfo=UTC),
            ),
        ]
    )
    db_session.commit()

    mock_prices = [
        {"date": "2026-01-02", "close": 100.0},
        {"date": "2026-01-05", "close": 110.0},
        {"date": "2026-01-06", "close": 120.0},
        {"date": "2026-01-07", "close": 130.0},
        {"date": "2026-01-08", "close": 140.0},
        {"date": "2026-01-09", "close": 150.0},
    ]

    invalidate_backtest_cache()
    with patch(
        "application.scan.backtest_service.get_price_history",
        return_value=mock_prices,
    ):
        summary = get_backtest_summary(db_session)

    assert summary["total_signals_evaluated"] == 1
    assert len(summary["signals"]) == 1
    assert summary["signals"][0]["signal"] == "OVERSOLD"
    assert summary["signals"][0]["total_occurrences"] == 1


def test_get_backtest_summary_should_use_cache_until_invalidated(db_session) -> None:
    _seed_stock(db_session, "MSFT")
    db_session.add(
        ScanLog(
            stock_ticker="MSFT",
            signal="CAUTION_HIGH",
            market_status="BEARISH",
            scanned_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
    )
    db_session.commit()

    mock_prices = [
        {"date": "2026-01-02", "close": 100.0},
        {"date": "2026-01-03", "close": 99.0},
        {"date": "2026-01-06", "close": 98.0},
    ]

    invalidate_backtest_cache()
    with patch(
        "application.scan.backtest_service.get_price_history",
        return_value=mock_prices,
    ) as mocked_get_price_history:
        get_backtest_summary(db_session)
        get_backtest_summary(db_session)

    assert mocked_get_price_history.call_count == 1

    invalidate_backtest_cache()
    with patch(
        "application.scan.backtest_service.get_price_history",
        return_value=mock_prices,
    ) as mocked_get_price_history_again:
        get_backtest_summary(db_session)
    assert mocked_get_price_history_again.call_count == 1


def test_get_backtest_detail_should_return_occurrences_for_signal(db_session) -> None:
    _seed_stock(db_session, "NVDA")
    db_session.add(
        ScanLog(
            stock_ticker="NVDA",
            signal="OVERHEATED",
            market_status="BULLISH",
            scanned_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
    )
    db_session.commit()

    mock_prices = [
        {"date": "2026-01-02", "close": 200.0},
        {"date": "2026-01-03", "close": 190.0},
        {"date": "2026-01-06", "close": 180.0},
    ]

    invalidate_backtest_cache()
    with patch(
        "application.scan.backtest_service.get_price_history",
        return_value=mock_prices,
    ):
        detail = get_backtest_detail(db_session, "OVERHEATED")

    assert detail is not None
    assert detail["signal"] == "OVERHEATED"
    assert len(detail["occurrences"]) == 1
    assert detail["occurrences"][0]["ticker"] == "NVDA"
