"""Tests for fundamentals fetching and caching in market_data."""

from unittest.mock import patch

from cachetools import TTLCache

from infrastructure.market_data.market_data import (
    _fetch_fundamentals_from_yf,
    _yf_dividend_data,
    get_fundamentals,
)


def _fresh_fundamentals_l1() -> TTLCache:
    return TTLCache(maxsize=100, ttl=300)


class TestFetchFundamentalsFromYf:
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_map_expected_fields(self, mock_yf_info):
        mock_yf_info.return_value = {
            "trailingPE": 20.1,
            "forwardPE": 18.4,
            "trailingEps": 6.2,
            "forwardEps": 6.8,
            "marketCap": 1_000_000_000,
            "priceToBook": 4.3,
            "priceToSalesTrailing12Months": 7.2,
            "profitMargins": 0.22,
            "operatingMargins": 0.28,
            "returnOnEquity": 0.31,
            "revenueGrowth": 0.12,
            "earningsGrowth": 0.15,
        }

        result = _fetch_fundamentals_from_yf("NVDA")

        assert result["ticker"] == "NVDA"
        assert result["trailing_pe"] == 20.1
        assert result["market_cap"] == 1_000_000_000
        assert result["return_on_equity"] == 0.31

    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_return_all_none_when_exception(self, mock_yf_info):
        mock_yf_info.side_effect = Exception("boom")

        result = _fetch_fundamentals_from_yf("FAIL")

        assert result["ticker"] == "FAIL"
        assert result["trailing_pe"] is None
        assert result["market_cap"] is None
        assert result["earnings_growth"] is None


class TestGetFundamentals:
    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_fundamentals_from_yf")
    def test_should_cache_in_l1_and_l2(self, mock_fetch, mock_disk_set, mock_disk_get):
        mock_disk_get.return_value = None
        mock_fetch.return_value = {"ticker": "AAPL", "trailing_pe": 24.1}

        with patch(
            "infrastructure.market_data.market_data._fundamentals_cache",
            _fresh_fundamentals_l1(),
        ) as l1:
            result = get_fundamentals("AAPL")

            assert result["trailing_pe"] == 24.1
            cached = l1.get("AAPL")
            assert cached is not None
            assert cached["trailing_pe"] == 24.1
            mock_disk_set.assert_called_once()


class TestYfDividendData:
    @patch("infrastructure.market_data.market_data._yf_dividends")
    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_reuse_yf_info_and_fetch_dividends(
        self, mock_yf_info, mock_yf_dividends
    ):
        mock_yf_info.return_value = {"ticker": "AAPL"}
        mock_yf_dividends.return_value = object()

        info, dividends = _yf_dividend_data("AAPL")

        assert info == {"ticker": "AAPL"}
        assert dividends is mock_yf_dividends.return_value
        mock_yf_info.assert_called_once_with("AAPL")
        mock_yf_dividends.assert_called_once_with("AAPL")
