"""
Tests for new market-data wrapper methods added to stock_service.py.
All infrastructure.market_data calls are mocked — no network I/O.
"""

from unittest.mock import patch

STOCK_MODULE = "application.stock_service"


class TestGetSignalsForTicker:
    def test_returns_signals_with_bias_distribution(self) -> None:
        mock_signals = {"rsi": 55.0, "bias": 10.0}
        mock_dist = {"historical_biases": [1.0, 2.0], "count": 2}
        with patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals):
            with patch(f"{STOCK_MODULE}.get_bias_distribution", return_value=mock_dist):
                from application.stock_service import get_signals_for_ticker

                result = get_signals_for_ticker("AAPL")

        assert result["rsi"] == 55.0
        assert result["bias_distribution"] == mock_dist

    def test_returns_signals_unchanged_when_signals_none(self) -> None:
        with patch(f"{STOCK_MODULE}.get_technical_signals", return_value=None):
            with patch(f"{STOCK_MODULE}.get_bias_distribution") as mock_dist:
                from application.stock_service import get_signals_for_ticker

                result = get_signals_for_ticker("AAPL")

        assert result is None
        mock_dist.assert_not_called()


class TestGetPriceHistory:
    def test_delegates_to_infrastructure(self) -> None:
        mock_history = [{"date": "2024-01-01", "close": 100.0}]
        with patch(f"{STOCK_MODULE}._get_price_history", return_value=mock_history):
            from application.stock_service import get_price_history

            result = get_price_history("AAPL")

        assert result == mock_history

    def test_returns_none_when_not_available(self) -> None:
        with patch(f"{STOCK_MODULE}._get_price_history", return_value=None):
            from application.stock_service import get_price_history

            result = get_price_history("UNKNOWN")

        assert result is None


class TestGetEarningsForTicker:
    def test_returns_earnings_date(self) -> None:
        mock_earnings = {"next_earnings_date": "2025-04-30"}
        with patch(f"{STOCK_MODULE}.get_earnings_date", return_value=mock_earnings):
            from application.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker("AAPL")

        assert result == mock_earnings

    def test_returns_none_when_not_available(self) -> None:
        with patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None):
            from application.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker("AAPL")

        assert result is None


class TestGetDividendForTicker:
    def test_returns_dividend_info(self) -> None:
        mock_div = {"yield": 0.5, "amount": 0.25}
        with patch(f"{STOCK_MODULE}.get_dividend_info", return_value=mock_div):
            from application.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker("AAPL")

        assert result == mock_div

    def test_returns_none_when_not_available(self) -> None:
        with patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None):
            from application.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker("AAPL")

        assert result is None
