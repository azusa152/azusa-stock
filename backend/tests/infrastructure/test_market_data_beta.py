"""
Tests for Beta fetching logic (for stress test feature).

Covers:
- _fetch_beta_from_yf returns Beta or sentinel value (_BETA_NOT_AVAILABLE).
- get_stock_beta converts sentinel to None for callers.
- get_stock_beta respects L1 and L2 cache.
- prewarm_beta_batch fetches multiple tickers concurrently.
- Sentinel value caching prevents repeated yfinance calls for unavailable Beta.
"""

import os
import tempfile

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_beta"
)

from unittest.mock import patch  # noqa: E402

from cachetools import TTLCache  # noqa: E402

from infrastructure.market_data.market_data import (  # noqa: E402
    _BETA_NOT_AVAILABLE,
    _fetch_beta_from_yf,
    get_stock_beta,
    prewarm_beta_batch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_beta_l1() -> TTLCache:
    """Create a fresh L1 Beta cache for test isolation."""
    return TTLCache(maxsize=100, ttl=86400)


# ---------------------------------------------------------------------------
# _fetch_beta_from_yf — basic fetching behavior
# ---------------------------------------------------------------------------


class TestFetchBetaFromYf:
    """Verify _fetch_beta_from_yf returns Beta or sentinel value."""

    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_return_beta_when_yfinance_provides_it(self, mock_yf_info):
        # Arrange
        mock_yf_info.return_value = {"beta": 1.23456}

        # Act
        result = _fetch_beta_from_yf("NVDA")

        # Assert
        assert result == 1.23  # Rounded to 2 decimals
        mock_yf_info.assert_called_once_with("NVDA")

    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_return_sentinel_when_beta_is_none(self, mock_yf_info):
        # Arrange
        mock_yf_info.return_value = {"beta": None}

        # Act
        result = _fetch_beta_from_yf("BTC-USD")

        # Assert
        assert result == _BETA_NOT_AVAILABLE
        mock_yf_info.assert_called_once_with("BTC-USD")

    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_return_sentinel_when_beta_key_missing(self, mock_yf_info):
        # Arrange — info dict doesn't contain "beta" key
        mock_yf_info.return_value = {"shortName": "Some Stock"}

        # Act
        result = _fetch_beta_from_yf("UNKNOWN")

        # Assert
        assert result == _BETA_NOT_AVAILABLE
        mock_yf_info.assert_called_once_with("UNKNOWN")

    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_return_sentinel_when_yf_info_raises_exception(self, mock_yf_info):
        # Arrange
        mock_yf_info.side_effect = Exception("yfinance failed")

        # Act
        result = _fetch_beta_from_yf("FAIL")

        # Assert
        assert result == _BETA_NOT_AVAILABLE
        mock_yf_info.assert_called_once_with("FAIL")

    @patch("infrastructure.market_data.market_data._yf_info")
    def test_should_round_beta_to_two_decimals(self, mock_yf_info):
        # Arrange
        mock_yf_info.return_value = {"beta": 1.987654321}

        # Act
        result = _fetch_beta_from_yf("TSLA")

        # Assert
        assert result == 1.99


# ---------------------------------------------------------------------------
# get_stock_beta — L1 + L2 cache and sentinel conversion
# ---------------------------------------------------------------------------


class TestGetStockBeta:
    """Verify get_stock_beta caching and sentinel-to-None conversion."""

    @patch("infrastructure.market_data.market_data._cached_fetch")
    def test_should_return_beta_when_available(self, mock_cached_fetch):
        # Arrange
        mock_cached_fetch.return_value = 1.25

        # Act
        result = get_stock_beta("AAPL")

        # Assert
        assert result == 1.25
        mock_cached_fetch.assert_called_once()

    @patch("infrastructure.market_data.market_data._cached_fetch")
    def test_should_convert_sentinel_to_none(self, mock_cached_fetch):
        # Arrange — _cached_fetch returns sentinel
        mock_cached_fetch.return_value = _BETA_NOT_AVAILABLE

        # Act
        result = get_stock_beta("BTC-USD")

        # Assert — public API returns None (not sentinel)
        assert result is None
        mock_cached_fetch.assert_called_once()

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_cache_sentinel_in_l1_and_l2(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — L1 and L2 both empty
        mock_disk_get.return_value = None
        mock_fetch.return_value = _BETA_NOT_AVAILABLE

        # Patch the actual _beta_cache to observe L1 behavior
        with patch(
            "infrastructure.market_data.market_data._beta_cache", _fresh_beta_l1()
        ) as l1:
            # Act
            result = get_stock_beta("CRYPTO")

            # Assert — result is None for caller
            assert result is None
            # Assert — sentinel stored in L1
            assert l1.get("CRYPTO") == _BETA_NOT_AVAILABLE
            # Assert — sentinel stored in L2 (no is_error callback for Beta)
            mock_disk_set.assert_called_once()
            call_args = mock_disk_set.call_args
            assert call_args[0][1] == _BETA_NOT_AVAILABLE  # value argument

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_cache_success_beta_in_l1_and_l2(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange
        mock_disk_get.return_value = None
        mock_fetch.return_value = 1.45

        with patch(
            "infrastructure.market_data.market_data._beta_cache", _fresh_beta_l1()
        ) as l1:
            # Act
            result = get_stock_beta("NVDA")

            # Assert
            assert result == 1.45
            assert l1.get("NVDA") == 1.45
            mock_disk_set.assert_called_once()
            call_args = mock_disk_set.call_args
            assert call_args[0][1] == 1.45

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_return_l1_cached_without_fetching(self, mock_fetch, mock_disk_get):
        # Arrange — pre-populate L1
        l1 = _fresh_beta_l1()
        l1["MSFT"] = 1.12

        with patch("infrastructure.market_data.market_data._beta_cache", l1):
            # Act
            result = get_stock_beta("MSFT")

            # Assert
            assert result == 1.12
            mock_fetch.assert_not_called()
            mock_disk_get.assert_not_called()

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_promote_l2_to_l1_without_fetching(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — L1 empty, L2 has data
        mock_disk_get.return_value = 0.88

        with patch(
            "infrastructure.market_data.market_data._beta_cache", _fresh_beta_l1()
        ) as l1:
            # Act
            result = get_stock_beta("TLT")

            # Assert
            assert result == 0.88
            # Assert — L1 now has the value (promoted from L2)
            assert l1.get("TLT") == 0.88
            # Assert — fetcher never called (L2 hit)
            mock_fetch.assert_not_called()
            # Assert — disk_set not called (already in L2)
            mock_disk_set.assert_not_called()

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_convert_l2_sentinel_to_none(self, mock_fetch, mock_disk_get):
        # Arrange — L2 contains sentinel
        mock_disk_get.return_value = _BETA_NOT_AVAILABLE

        with patch(
            "infrastructure.market_data.market_data._beta_cache", _fresh_beta_l1()
        ) as l1:
            # Act
            result = get_stock_beta("OLD-CRYPTO")

            # Assert — public API returns None
            assert result is None
            # Assert — L1 has sentinel (promoted from L2)
            assert l1.get("OLD-CRYPTO") == _BETA_NOT_AVAILABLE
            # Assert — fetcher never called (L2 hit)
            mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# prewarm_beta_batch — concurrent fetching
# ---------------------------------------------------------------------------


class TestPrewarmBetaBatch:
    """Verify prewarm_beta_batch fetches multiple tickers concurrently."""

    @patch("infrastructure.market_data.market_data.get_stock_beta")
    def test_should_fetch_all_tickers(self, mock_get_beta):
        # Arrange
        mock_get_beta.side_effect = lambda t: {
            "NVDA": 1.5,
            "AAPL": 1.2,
            "TLT": 0.3,
        }.get(t, 1.0)

        # Act
        results = prewarm_beta_batch(["NVDA", "AAPL", "TLT"])

        # Assert
        assert results == {"NVDA": 1.5, "AAPL": 1.2, "TLT": 0.3}
        assert mock_get_beta.call_count == 3

    @patch("infrastructure.market_data.market_data.get_stock_beta")
    def test_should_return_none_for_unavailable_beta(self, mock_get_beta):
        # Arrange — some tickers have no Beta
        mock_get_beta.side_effect = lambda t: {"NVDA": 1.5, "BTC-USD": None}.get(t, 1.0)

        # Act
        results = prewarm_beta_batch(["NVDA", "BTC-USD"])

        # Assert
        assert results == {"NVDA": 1.5, "BTC-USD": None}

    @patch("infrastructure.market_data.market_data.get_stock_beta")
    def test_should_handle_exception_gracefully(self, mock_get_beta):
        # Arrange — one ticker raises exception
        def side_effect(ticker):
            if ticker == "FAIL":
                raise Exception("Fetch failed")
            return 1.0

        mock_get_beta.side_effect = side_effect

        # Act
        results = prewarm_beta_batch(["NVDA", "FAIL", "AAPL"])

        # Assert — failed ticker gets None
        assert results == {"NVDA": 1.0, "FAIL": None, "AAPL": 1.0}

    @patch("infrastructure.market_data.market_data.get_stock_beta")
    def test_should_return_empty_dict_for_empty_input(self, mock_get_beta):
        # Act
        results = prewarm_beta_batch([])

        # Assert
        assert results == {}
        mock_get_beta.assert_not_called()

    @patch("infrastructure.market_data.market_data.get_stock_beta")
    def test_should_fetch_concurrently_with_custom_max_workers(self, mock_get_beta):
        # Arrange
        mock_get_beta.side_effect = lambda t: 1.0

        # Act
        results = prewarm_beta_batch(["A", "B", "C", "D"], max_workers=2)

        # Assert
        assert len(results) == 4
        assert all(v == 1.0 for v in results.values())


# ---------------------------------------------------------------------------
# Sentinel value caching behavior
# ---------------------------------------------------------------------------


class TestBetaSentinelCaching:
    """Verify that sentinel values are properly cached to avoid repeated fetches."""

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_not_refetch_when_sentinel_in_l1(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — L1 has sentinel from previous call
        l1 = _fresh_beta_l1()
        l1["BTC-USD"] = _BETA_NOT_AVAILABLE

        with patch("infrastructure.market_data.market_data._beta_cache", l1):
            # Act — call get_stock_beta twice
            result1 = get_stock_beta("BTC-USD")
            result2 = get_stock_beta("BTC-USD")

            # Assert — both return None
            assert result1 is None
            assert result2 is None
            # Assert — fetcher never called (L1 cached sentinel)
            mock_fetch.assert_not_called()
            mock_disk_get.assert_not_called()

    @patch("infrastructure.market_data.market_data._disk_get")
    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_beta_from_yf")
    def test_should_not_refetch_when_sentinel_in_l2(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — L2 has sentinel, L1 empty
        mock_disk_get.return_value = _BETA_NOT_AVAILABLE

        with patch(
            "infrastructure.market_data.market_data._beta_cache", _fresh_beta_l1()
        ) as l1:
            # Act — call get_stock_beta twice
            result1 = get_stock_beta("ETH-USD")
            result2 = get_stock_beta("ETH-USD")

            # Assert
            assert result1 is None
            assert result2 is None
            # Assert — fetcher never called
            mock_fetch.assert_not_called()
            # Assert — disk_get called once (L2 hit on first call)
            # Second call hits L1 (promoted from L2)
            assert mock_disk_get.call_count == 1
            # Assert — L1 now has sentinel (promoted)
            assert l1.get("ETH-USD") == _BETA_NOT_AVAILABLE
