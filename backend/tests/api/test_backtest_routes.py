from datetime import UTC, datetime

from sqlmodel import Session

from domain.entities import ScanLog, Stock
from domain.enums import StockCategory
from tests.conftest import test_engine


def test_backtest_summary_route_should_return_200_with_response_shape(client) -> None:
    client.post(
        "/ticker",
        json={"ticker": "AAPL", "category": "Growth", "thesis": "test"},
    )

    with Session(test_engine) as session:
        session.add(
            ScanLog(
                stock_ticker="AAPL",
                signal="OVERSOLD",
                market_status="BULLISH",
                scanned_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
        )
        session.commit()

    resp = client.get("/backtest/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "signals" in data
    assert "computed_at" in data
    assert "lookback_days" in data
    assert "total_signals_evaluated" in data


def test_backtest_signal_detail_route_should_return_200_for_existing_signal(
    client,
) -> None:
    client.post(
        "/ticker",
        json={"ticker": "MSFT", "category": "Growth", "thesis": "test"},
    )
    with Session(test_engine) as session:
        stock = session.get(Stock, "MSFT")
        assert stock is not None
        stock.category = StockCategory.GROWTH
        session.add(
            ScanLog(
                stock_ticker="MSFT",
                signal="OVERHEATED",
                market_status="BULLISH",
                scanned_at=datetime(2026, 1, 2, tzinfo=UTC),
            )
        )
        session.commit()

    resp = client.get("/backtest/signal/OVERHEATED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal"] == "OVERHEATED"
    assert "summary" in data
    assert "occurrences" in data
    assert "total_occurrences" in data
    assert isinstance(data["total_occurrences"], int)


def test_backtest_signal_detail_route_should_return_404_for_unknown_signal(
    client,
) -> None:
    resp = client.get("/backtest/signal/NOT_A_SIGNAL")
    assert resp.status_code == 404


def test_backfill_status_route_should_return_200_with_response_shape(client) -> None:
    resp = client.get("/backtest/backfill-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_backfilling" in data
    assert "total" in data
    assert "completed" in data


def test_backtest_export_csv_route_should_return_csv_with_header(client) -> None:
    resp = client.get("/backtest/export-csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="backtest_signals.csv"' in resp.headers.get(
        "content-disposition", ""
    )

    first_line = resp.text.splitlines()[0]
    assert first_line == (
        "signal,direction,ticker,signal_date,market_status,return_5d,"
        "return_10d,return_30d,return_60d"
    )
