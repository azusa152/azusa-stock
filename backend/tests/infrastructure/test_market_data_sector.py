"""
Tests for sector cache functions.

Covers:
- get_ticker_sector_cached: cache hit/miss/sentinel/empty ticker behaviour.
- get_etf_sector_weights: key normalization, list format, empty/None handling,
  non-ETF ticker, and cache sentinel deduplication.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_sector"
)

from infrastructure.market_data import (  # noqa: E402
    _ETF_SECTOR_KEY_MAP,
    _SECTOR_NOT_FOUND,
    _disk_set,
    _etf_sector_weights_cache,
    get_etf_sector_weights,
    get_ticker_sector_cached,
)
from domain.constants import DISK_KEY_SECTOR, DISK_SECTOR_TTL  # noqa: E402


class TestGetTickerSectorCached:
    """get_ticker_sector_cached reads disk cache only — never triggers yfinance."""

    def test_returns_sector_on_cache_hit(self):
        _disk_set(f"{DISK_KEY_SECTOR}:AAPL", "Technology", DISK_SECTOR_TTL)
        assert get_ticker_sector_cached("AAPL") == "Technology"

    def test_returns_none_on_cache_miss(self):
        result = get_ticker_sector_cached("NONEXISTENT_TICKER_XYZ")
        assert result is None

    def test_returns_none_for_sector_not_found_sentinel(self):
        _disk_set(f"{DISK_KEY_SECTOR}:BOND_ETF", _SECTOR_NOT_FOUND, DISK_SECTOR_TTL)
        assert get_ticker_sector_cached("BOND_ETF") is None

    def test_returns_none_for_empty_ticker(self):
        assert get_ticker_sector_cached("") is None

    def test_returns_none_for_none_ticker(self):
        assert get_ticker_sector_cached(None) is None

    @patch("infrastructure.market_data._fetch_sector_from_yf")
    def test_never_calls_yfinance(self, mock_yf):
        get_ticker_sector_cached("WHATEVER")
        mock_yf.assert_not_called()


def _make_funds_data(sector_weightings):
    """Build a mock yfinance Ticker with funds_data.sector_weightings."""
    fd = MagicMock()
    fd.sector_weightings = sector_weightings
    ticker_obj = MagicMock()
    ticker_obj.funds_data = fd
    return ticker_obj


class TestGetEtfSectorWeights:
    """get_etf_sector_weights fetches and normalizes ETF sector weight data."""

    def setup_method(self):
        """Clear L1 cache before each test to prevent cross-test contamination."""
        _etf_sector_weights_cache.clear()

    @patch("infrastructure.market_data._yf_ticker_obj")
    @patch("infrastructure.market_data._rate_limiter")
    def test_should_return_normalized_gics_names_for_dict_format(
        self, _mock_rl, mock_ticker
    ):
        """Dict format with snake_case keys → normalized GICS sector names."""
        mock_ticker.return_value = _make_funds_data(
            {"technology": 0.30, "consumer_cyclical": 0.12, "realestate": 0.05}
        )
        result = get_etf_sector_weights("VTI_DICT_TEST")
        assert result == {
            "Technology": 0.30,
            "Consumer Cyclical": 0.12,
            "Real Estate": 0.05,
        }

    @patch("infrastructure.market_data._yf_ticker_obj")
    @patch("infrastructure.market_data._rate_limiter")
    def test_should_handle_list_of_dicts_format(self, _mock_rl, mock_ticker):
        """list[dict] format (older yfinance) merges correctly into a single dict."""
        mock_ticker.return_value = _make_funds_data(
            [{"technology": 0.28, "financial_services": 0.14}]
        )
        result = get_etf_sector_weights("VTI_LIST_TEST")
        assert result is not None
        assert result["Technology"] == 0.28
        assert result["Financial Services"] == 0.14

    @patch("infrastructure.market_data._yf_ticker_obj")
    @patch("infrastructure.market_data._rate_limiter")
    def test_should_fall_back_to_title_for_unmapped_key(self, _mock_rl, mock_ticker):
        """Keys not in _ETF_SECTOR_KEY_MAP fall back to str.title()."""
        mock_ticker.return_value = _make_funds_data({"other": 0.03})
        result = get_etf_sector_weights("VTI_UNKNOWN_KEY_TEST")
        assert result == {"Other": 0.03}

    @patch("infrastructure.market_data._yf_ticker_obj")
    @patch("infrastructure.market_data._rate_limiter")
    def test_should_return_none_when_sector_weightings_is_none(
        self, _mock_rl, mock_ticker
    ):
        """None sector_weightings → returns None."""
        mock_ticker.return_value = _make_funds_data(None)
        result = get_etf_sector_weights("NON_ETF_NONE_TEST")
        assert result is None

    @patch("infrastructure.market_data._yf_ticker_obj")
    @patch("infrastructure.market_data._rate_limiter")
    def test_should_return_none_when_sector_weightings_is_empty(
        self, _mock_rl, mock_ticker
    ):
        """Empty dict sector_weightings → returns None."""
        mock_ticker.return_value = _make_funds_data({})
        result = get_etf_sector_weights("NON_ETF_EMPTY_TEST")
        assert result is None

    @patch("infrastructure.market_data._yf_ticker_obj")
    @patch("infrastructure.market_data._rate_limiter")
    def test_should_return_none_when_funds_data_is_none(self, _mock_rl, mock_ticker):
        """funds_data is None (non-ETF stock) → returns None."""
        ticker_obj = MagicMock()
        ticker_obj.funds_data = None
        mock_ticker.return_value = ticker_obj
        result = get_etf_sector_weights("AAPL_STOCK_TEST")
        assert result is None

    @patch("infrastructure.market_data._fetch_etf_sector_weights")
    def test_should_not_call_yfinance_on_second_call_for_non_etf(self, mock_fetch):
        """Sentinel caching: non-ETF returns None on first call, then no yfinance on repeat."""
        mock_fetch.return_value = None  # non-ETF sentinel path

        first = get_etf_sector_weights("CACHE_SENTINEL_TEST_STOCK")
        second = get_etf_sector_weights("CACHE_SENTINEL_TEST_STOCK")

        assert first is None
        assert second is None
        # fetcher called only once; second call served from L1 cache
        mock_fetch.assert_called_once_with("CACHE_SENTINEL_TEST_STOCK")

    def test_key_map_covers_all_standard_gics_sectors(self):
        """_ETF_SECTOR_KEY_MAP covers the 11 standard GICS sectors."""
        expected_gics = {
            "Technology",
            "Consumer Cyclical",
            "Financial Services",
            "Real Estate",
            "Consumer Defensive",
            "Healthcare",
            "Utilities",
            "Communication Services",
            "Energy",
            "Industrials",
            "Basic Materials",
        }
        assert set(_ETF_SECTOR_KEY_MAP.values()) == expected_gics
