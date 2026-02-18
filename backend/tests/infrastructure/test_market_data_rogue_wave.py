"""
Tests for get_bias_distribution() — Rogue Wave (瘋狗浪) infrastructure layer.

Covers:
- _fetch_bias_distribution_from_yf: bias array is sorted, p95 is correct,
  graceful fallback on empty/insufficient data, graceful fallback on exception.
- get_bias_distribution: L1 cache hit, L2 cache hit + promotion, fetcher called
  on cold cache, error result not written to L2 (is_error guard).
- clear_all_caches: _rogue_wave_cache is included.
"""

import os
import tempfile

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_rogue_wave"
)

from unittest.mock import MagicMock, patch  # noqa: E402

import pandas as pd  # noqa: E402
from cachetools import TTLCache  # noqa: E402

from infrastructure.market_data import (  # noqa: E402
    _fetch_bias_distribution_from_yf,
    _rogue_wave_cache,
    clear_all_caches,
    get_bias_distribution,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hist(n: int, price: float = 100.0) -> pd.DataFrame:
    """Return a minimal yfinance-like history DataFrame with n rows."""
    import numpy as np

    # Use a fixed seed for reproducibility; gentle upward drift
    rng = np.random.default_rng(42)
    closes = price + rng.normal(0, 2, n).cumsum()
    closes = [max(1.0, round(float(c), 2)) for c in closes]
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    return pd.DataFrame({"Close": closes, "Volume": [1_000_000] * n}, index=idx)


def _fresh_rogue_wave_l1() -> TTLCache:
    return TTLCache(maxsize=200, ttl=86400)


# ---------------------------------------------------------------------------
# _fetch_bias_distribution_from_yf
# ---------------------------------------------------------------------------


class TestFetchBiasDistributionFromYf:
    """Unit tests for the raw yfinance fetcher."""

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_sorted_bias_array(self, mock_yf_history):
        # Arrange: 300 trading days — enough to compute ≥200 MA60-eligible rows
        hist = _make_hist(300)
        mock_yf_history.return_value = (MagicMock(), hist)

        # Act
        result = _fetch_bias_distribution_from_yf("AAPL")

        # Assert
        assert "historical_biases" in result
        biases = result["historical_biases"]
        assert biases == sorted(biases), "historical_biases must be sorted ascending"

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_correct_count(self, mock_yf_history):
        hist = _make_hist(300)
        mock_yf_history.return_value = (MagicMock(), hist)

        result = _fetch_bias_distribution_from_yf("AAPL")

        assert result["count"] == len(result["historical_biases"])

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_p95_as_95th_percentile(self, mock_yf_history):
        hist = _make_hist(300)
        mock_yf_history.return_value = (MagicMock(), hist)

        result = _fetch_bias_distribution_from_yf("AAPL")

        biases = result["historical_biases"]
        expected_idx = int(len(biases) * 0.95)
        expected_p95 = round(biases[min(expected_idx, len(biases) - 1)], 2)
        assert result["p95"] == expected_p95

    @patch("infrastructure.market_data._yf_history")
    def test_should_include_fetched_at_timestamp(self, mock_yf_history):
        hist = _make_hist(300)
        mock_yf_history.return_value = (MagicMock(), hist)

        result = _fetch_bias_distribution_from_yf("AAPL")

        assert "fetched_at" in result
        assert result["fetched_at"]  # non-empty string

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_empty_dict_when_history_empty(self, mock_yf_history):
        mock_yf_history.return_value = (MagicMock(), pd.DataFrame())

        result = _fetch_bias_distribution_from_yf("EMPTY")

        assert result == {}

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_empty_dict_when_insufficient_data(self, mock_yf_history):
        # Only 100 rows — MA60 gives ~40 bias points, below MIN_HISTORY_DAYS=200
        hist = _make_hist(100)
        mock_yf_history.return_value = (MagicMock(), hist)

        result = _fetch_bias_distribution_from_yf("SHORT")

        assert result == {}

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_empty_dict_on_yfinance_exception(self, mock_yf_history):
        mock_yf_history.side_effect = Exception("network error")

        result = _fetch_bias_distribution_from_yf("FAIL")

        assert result == {}

    @patch("infrastructure.market_data._yf_history")
    def test_should_return_floats_in_bias_array(self, mock_yf_history):
        hist = _make_hist(300)
        mock_yf_history.return_value = (MagicMock(), hist)

        result = _fetch_bias_distribution_from_yf("NVDA")

        assert all(isinstance(b, float) for b in result["historical_biases"])

    @patch("infrastructure.market_data._yf_history")
    def test_should_call_yf_history_with_3y_period(self, mock_yf_history):
        hist = _make_hist(300)
        mock_yf_history.return_value = (MagicMock(), hist)

        _fetch_bias_distribution_from_yf("TSLA")

        mock_yf_history.assert_called_once_with("TSLA", "3y")


# ---------------------------------------------------------------------------
# get_bias_distribution — L1 / L2 cache behaviour
# ---------------------------------------------------------------------------


class TestGetBiasDistribution:
    """Verify get_bias_distribution uses _cached_fetch correctly."""

    @patch("infrastructure.market_data._disk_get")
    @patch("infrastructure.market_data._fetch_bias_distribution_from_yf")
    def test_should_return_l1_cached_without_fetching(self, mock_fetch, mock_disk_get):
        # Arrange — pre-populate L1
        cached_data = {"historical_biases": [1.0, 2.0], "count": 2, "p95": 2.0}
        l1 = _fresh_rogue_wave_l1()
        l1["AAPL"] = cached_data

        with patch("infrastructure.market_data._rogue_wave_cache", l1):
            result = get_bias_distribution("AAPL")

        assert result == cached_data
        mock_fetch.assert_not_called()
        mock_disk_get.assert_not_called()

    @patch("infrastructure.market_data._disk_get")
    @patch("infrastructure.market_data._disk_set")
    @patch("infrastructure.market_data._fetch_bias_distribution_from_yf")
    def test_should_promote_l2_to_l1_without_fetching(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — L2 has valid data
        l2_data = {"historical_biases": [0.5, 1.5], "count": 2, "p95": 1.5}
        mock_disk_get.return_value = l2_data

        with patch(
            "infrastructure.market_data._rogue_wave_cache", _fresh_rogue_wave_l1()
        ):
            result = get_bias_distribution("NVDA")

        assert result == l2_data
        mock_fetch.assert_not_called()
        mock_disk_set.assert_not_called()  # already in L2, no re-write needed

    @patch("infrastructure.market_data._disk_get")
    @patch("infrastructure.market_data._disk_set")
    @patch("infrastructure.market_data._fetch_bias_distribution_from_yf")
    def test_should_write_l1_and_l2_on_cache_miss(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — cold cache
        fresh_data = {
            "historical_biases": [1.0, 2.0, 3.0],
            "count": 3,
            "p95": 3.0,
            "fetched_at": "2026-02-18T00:00:00+00:00",
        }
        mock_disk_get.return_value = None
        mock_fetch.return_value = fresh_data

        with patch(
            "infrastructure.market_data._rogue_wave_cache", _fresh_rogue_wave_l1()
        ):
            result = get_bias_distribution("MSFT")

        assert result == fresh_data
        mock_fetch.assert_called_once_with("MSFT")
        # L2 should have been written (valid result)
        mock_disk_set.assert_called_once()
        disk_key_arg = mock_disk_set.call_args[0][0]
        assert "rogue_wave" in disk_key_arg

    @patch("infrastructure.market_data._disk_get")
    @patch("infrastructure.market_data._disk_set")
    @patch("infrastructure.market_data._fetch_bias_distribution_from_yf")
    def test_should_not_write_l2_when_fetcher_returns_empty(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Arrange — fetcher returns empty dict (error)
        mock_disk_get.return_value = None
        mock_fetch.return_value = {}

        with patch(
            "infrastructure.market_data._rogue_wave_cache", _fresh_rogue_wave_l1()
        ):
            result = get_bias_distribution("FAIL")

        assert result == {}
        # is_error guard: empty result must NOT be persisted to L2
        mock_disk_set.assert_not_called()

    @patch("infrastructure.market_data._disk_get")
    @patch("infrastructure.market_data._disk_set")
    @patch("infrastructure.market_data._fetch_bias_distribution_from_yf")
    def test_should_cache_error_result_in_l1(
        self, mock_fetch, mock_disk_set, mock_disk_get
    ):
        # Even error results are stored in L1 (short-lived, prevents thundering herd)
        mock_disk_get.return_value = None
        mock_fetch.return_value = {}

        with patch(
            "infrastructure.market_data._rogue_wave_cache", _fresh_rogue_wave_l1()
        ) as l1:
            get_bias_distribution("FAIL")
            # L1 should have the empty dict stored
            assert l1.get("FAIL") == {}


# ---------------------------------------------------------------------------
# clear_all_caches includes _rogue_wave_cache
# ---------------------------------------------------------------------------


class TestClearAllCachesIncludesRogueWave:
    """Verify _rogue_wave_cache is cleared by clear_all_caches()."""

    def test_should_clear_rogue_wave_l1_cache(self):
        # Arrange — put something in the real _rogue_wave_cache
        _rogue_wave_cache["AAPL"] = {"historical_biases": [1.0], "count": 1}
        assert _rogue_wave_cache.get("AAPL") is not None

        # Act
        result = clear_all_caches()

        # Assert — cache is empty
        assert _rogue_wave_cache.get("AAPL") is None
        assert result["l1_cleared"] >= 12  # at least 12 L1 caches (was 11, now +1)
