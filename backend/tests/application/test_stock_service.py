"""
Tests for new market-data wrapper methods added to stock_service.py.
All infrastructure.market_data calls are mocked — no network I/O.
"""

from unittest.mock import patch

STOCK_MODULE = "application.stock.stock_service"


class TestGetSignalsForTicker:
    def test_returns_signals_with_bias_distribution(self) -> None:
        mock_signals = {"rsi": 55.0, "bias": 10.0}
        mock_dist = {"historical_biases": [1.0, 2.0], "count": 2}
        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_bias_distribution", return_value=mock_dist),
        ):
            from application.stock.stock_service import get_signals_for_ticker

            result = get_signals_for_ticker("AAPL")

        assert result["rsi"] == 55.0
        assert result["bias_distribution"] == mock_dist

    def test_returns_signals_unchanged_when_signals_none(self) -> None:
        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=None),
            patch(f"{STOCK_MODULE}.get_bias_distribution") as mock_dist,
        ):
            from application.stock.stock_service import get_signals_for_ticker

            result = get_signals_for_ticker("AAPL")

        assert result is None
        mock_dist.assert_not_called()


class TestGetPriceHistory:
    def test_delegates_to_infrastructure(self) -> None:
        mock_history = [{"date": "2024-01-01", "close": 100.0}]
        with patch(f"{STOCK_MODULE}._get_price_history", return_value=mock_history):
            from application.stock.stock_service import get_price_history

            result = get_price_history("AAPL")

        assert result == mock_history

    def test_returns_none_when_not_available(self) -> None:
        with patch(f"{STOCK_MODULE}._get_price_history", return_value=None):
            from application.stock.stock_service import get_price_history

            result = get_price_history("UNKNOWN")

        assert result is None


class TestGetEarningsForTicker:
    def test_returns_earnings_date(self) -> None:
        mock_earnings = {"next_earnings_date": "2025-04-30"}
        with patch(f"{STOCK_MODULE}.get_earnings_date", return_value=mock_earnings):
            from application.stock.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker("AAPL")

        assert result == mock_earnings

    def test_returns_none_when_not_available(self) -> None:
        with patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None):
            from application.stock.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker("AAPL")

        assert result is None


class TestGetDividendForTicker:
    def test_returns_dividend_info(self) -> None:
        mock_div = {"yield": 0.5, "amount": 0.25}
        with patch(f"{STOCK_MODULE}.get_dividend_info", return_value=mock_div):
            from application.stock.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker("AAPL")

        assert result == mock_div

    def test_returns_none_when_not_available(self) -> None:
        with patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None):
            from application.stock.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker("AAPL")

        assert result is None


# ===========================================================================
# list_removed_stocks
# ===========================================================================


class TestListRemovedStocks:
    def test_returns_empty_when_no_inactive_stocks(self, db_session) -> None:
        from application.stock.stock_service import list_removed_stocks

        result = list_removed_stocks(db_session)
        assert result == []

    def test_returns_inactive_stock_with_removal_reason(self, db_session) -> None:
        from domain.entities import RemovalLog, Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        stock = save_stock(
            db_session,
            Stock(ticker="REMOVED1", category=StockCategory.MOAT, is_active=False),
        )
        log = RemovalLog(stock_ticker=stock.ticker, reason="Thesis invalidated")
        db_session.add(log)
        db_session.commit()

        from application.stock.stock_service import list_removed_stocks

        result = list_removed_stocks(db_session)
        assert len(result) == 1
        assert result[0]["ticker"] == "REMOVED1"
        assert result[0]["removal_reason"] == "Thesis invalidated"

    def test_returns_unknown_reason_when_no_removal_log(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(
            db_session,
            Stock(ticker="REMOVED2", category=StockCategory.MOAT, is_active=False),
        )
        db_session.commit()

        from application.stock.stock_service import list_removed_stocks

        result = list_removed_stocks(db_session)
        match = next((r for r in result if r["ticker"] == "REMOVED2"), None)
        assert match is not None
        # No removal log → removal_reason should be a non-empty fallback string
        assert isinstance(match["removal_reason"], str)
        assert len(match["removal_reason"]) > 0


# ===========================================================================
# import_stocks
# ===========================================================================


class TestImportStocks:
    def test_creates_new_stock_on_import(self, db_session) -> None:
        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False):
            from application.stock.stock_service import import_stocks

            result = import_stocks(
                db_session,
                [{"ticker": "NEW1", "category": "Growth", "thesis": "Strong growth"}],
            )

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["errors"] == []

    def test_updates_existing_stock_on_import(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(
            db_session,
            Stock(ticker="EXIST1", category=StockCategory.MOAT),
        )

        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False):
            from application.stock.stock_service import import_stocks

            result = import_stocks(
                db_session,
                [{"ticker": "EXIST1", "category": "Moat", "thesis": "Updated thesis"}],
            )

        assert result["created"] == 0
        assert result["updated"] == 1

    def test_error_on_missing_ticker(self, db_session) -> None:
        from application.stock.stock_service import import_stocks

        result = import_stocks(db_session, [{"category": "Growth", "thesis": "Oops"}])

        assert result["created"] == 0
        assert len(result["errors"]) == 1

    def test_error_on_invalid_category(self, db_session) -> None:
        from application.stock.stock_service import import_stocks

        result = import_stocks(
            db_session,
            [{"ticker": "BAD1", "category": "INVALID_CAT", "thesis": "Bad category"}],
        )

        assert len(result["errors"]) == 1

    def test_is_etf_from_payload_overrides_auto_detect(self, db_session) -> None:
        with patch(f"{STOCK_MODULE}.detect_is_etf") as mock_detect:
            from application.stock.stock_service import import_stocks

            result = import_stocks(
                db_session,
                [
                    {
                        "ticker": "ETF1",
                        "category": "Growth",
                        "thesis": "",
                        "is_etf": True,
                    }
                ],
            )

        assert result["created"] == 1
        mock_detect.assert_not_called()

    def test_handles_empty_list(self, db_session) -> None:
        from application.stock.stock_service import import_stocks

        result = import_stocks(db_session, [])
        assert result["created"] == 0
        assert result["updated"] == 0


# ===========================================================================
# get_moat_for_ticker
# ===========================================================================


class TestGetMoatForTicker:
    def test_returns_na_for_bond_category(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="TLT", category=StockCategory.BOND))

        with patch(f"{STOCK_MODULE}.analyze_moat_trend") as mock_analyze:
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "TLT")

        assert result["moat"] == "N/A"
        assert "TLT" in result["ticker"]
        mock_analyze.assert_not_called()

    def test_returns_na_for_cash_category(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="CASH1", category=StockCategory.CASH))

        with patch(f"{STOCK_MODULE}.analyze_moat_trend") as mock_analyze:
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "CASH1")

        assert result["moat"] == "N/A"
        mock_analyze.assert_not_called()

    def test_delegates_to_analyze_moat_trend_for_moat_stocks(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category=StockCategory.MOAT))
        mock_moat = {"ticker": "AAPL", "moat": "護城河穩固", "yoy_change": 2.1}

        with patch(f"{STOCK_MODULE}.analyze_moat_trend", return_value=mock_moat):
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "AAPL")

        assert result["moat"] == "護城河穩固"

    def test_delegates_to_analyze_when_stock_not_in_db(self, db_session) -> None:
        """Stock not in DB should still call analyze_moat_trend (no category to skip)."""
        mock_moat = {"ticker": "UNKNOWN", "moat": "N/A"}

        with patch(f"{STOCK_MODULE}.analyze_moat_trend", return_value=mock_moat):
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "UNKNOWN")

        assert result["ticker"] == "UNKNOWN"


# ===========================================================================
# get_enriched_stocks
# ===========================================================================


class TestGetEnrichedStocks:
    def test_returns_empty_list_when_no_active_stocks(self, db_session) -> None:
        from application.stock.stock_service import get_enriched_stocks

        result = get_enriched_stocks(db_session)
        assert result == []

    def test_returns_enriched_data_for_active_stocks(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="NVDA", category=StockCategory.MOAT))

        mock_signals = {"rsi": 60.0, "bias": 5.0, "ma200": 100.0}
        mock_earnings = {"next_earnings_date": "2025-07-30"}
        mock_dividend = {"dividend_yield": 0.02}

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=mock_earnings),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=mock_dividend),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"
        assert result[0]["signals"] == mock_signals
        assert result[0]["earnings"] == mock_earnings
        assert result[0]["dividend"] == mock_dividend

    def test_thesis_broken_signal_preserved(self, db_session) -> None:
        """Stocks with THESIS_BROKEN last_scan_signal should keep computed_signal='THESIS_BROKEN'."""
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        stock = Stock(
            ticker="BROKEN1",
            category=StockCategory.MOAT,
            last_scan_signal="THESIS_BROKEN",
        )
        save_stock(db_session, stock)

        mock_signals = {"rsi": 50.0, "bias": 2.0}

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        broken = next(r for r in result if r["ticker"] == "BROKEN1")
        assert broken["computed_signal"] == "THESIS_BROKEN"

    def test_signals_skipped_for_cash_category(self, db_session) -> None:
        """Cash category stocks should not have signals fetched."""
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="CASH_A", category=StockCategory.CASH))

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals") as mock_signals,
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert len(result) == 1
        mock_signals.assert_not_called()
        assert result[0]["signals"] is None
