"""
Tests for batch_download_history() and prime_signals_cache_batch() in market_data.py.

Covers:
- batch_download_history returns empty dict for empty ticker list
- batch_download_history returns empty dict when yf.download() raises
- batch_download_history filters out tickers with insufficient history
- batch_download_history extracts per-ticker DataFrame correctly (multi-ticker)
- prime_signals_cache_batch skips tickers already in L1 cache
- prime_signals_cache_batch writes results to L1 and L2 on success
- prime_signals_cache_batch skips L2 write for error results
- prime_signals_cache_batch returns count of primed tickers
"""

import os
import tempfile

# Set environment variables BEFORE any app imports
os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_batch"
)

from unittest.mock import patch  # noqa: E402

import pandas as pd  # noqa: E402
from cachetools import TTLCache  # noqa: E402

from infrastructure.market_data import (  # noqa: E402
    batch_download_history,
    prime_signals_cache_batch,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_ROWS = 60  # MIN_HISTORY_DAYS_FOR_SIGNALS


def _make_hist(rows: int = _MIN_ROWS) -> pd.DataFrame:
    """Create a minimal OHLCV DataFrame with `rows` rows."""
    idx = pd.date_range("2024-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {
            "Open": 100.0,
            "High": 105.0,
            "Low": 95.0,
            "Close": 102.0,
            "Volume": 1_000_000,
        },
        index=idx,
    )


def _make_multi_ticker_data(tickers: list[str], rows: int = _MIN_ROWS) -> pd.DataFrame:
    """Simulate yf.download() multi-ticker output with MultiIndex columns."""
    hist = _make_hist(rows)
    frames = dict.fromkeys(tickers, hist)
    return pd.concat(frames, axis=1)


def _fresh_signals_l1() -> TTLCache:
    """Create a fresh L1 signals cache for test isolation."""
    return TTLCache(maxsize=200, ttl=300)


# ===========================================================================
# batch_download_history
# ===========================================================================


class TestBatchDownloadHistoryEmpty:
    """batch_download_history should return {} for trivially invalid inputs."""

    def test_should_return_empty_dict_for_empty_ticker_list(self):
        # Act
        result = batch_download_history([])

        # Assert
        assert result == {}

    @patch(
        "infrastructure.market_data.market_data.yf.download",
        side_effect=RuntimeError("network error"),
    )
    @patch("infrastructure.market_data.market_data._rate_limiter")
    def test_should_return_empty_dict_when_yf_download_raises(self, _mock_rl, _mock_dl):
        # Act — exception must be swallowed
        result = batch_download_history(["AAPL"])

        # Assert
        assert result == {}


class TestBatchDownloadHistoryFiltering:
    """batch_download_history should filter tickers with insufficient data."""

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data.yf.download")
    def test_should_exclude_ticker_with_insufficient_rows(self, mock_dl, _mock_rl):
        # Arrange — only 10 rows, below MIN_HISTORY_DAYS_FOR_SIGNALS=60
        short_hist = _make_hist(rows=10)
        mock_dl.return_value = short_hist

        # Act
        result = batch_download_history(["AAPL"])

        # Assert
        assert "AAPL" not in result

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data.yf.download")
    def test_should_include_ticker_with_sufficient_rows(self, mock_dl, _mock_rl):
        # Arrange — exactly MIN_HISTORY_DAYS_FOR_SIGNALS rows
        hist = _make_hist(rows=_MIN_ROWS)
        mock_dl.return_value = hist

        # Act
        result = batch_download_history(["AAPL"])

        # Assert
        assert "AAPL" in result
        assert len(result["AAPL"]) == _MIN_ROWS


class TestBatchDownloadHistoryMultiTicker:
    """batch_download_history extracts per-ticker slices from multi-ticker download."""

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data.yf.download")
    def test_should_return_per_ticker_dataframes_for_multi_ticker(
        self, mock_dl, _mock_rl
    ):
        # Arrange — simulate yf.download(["AAPL", "MSFT"]) MultiIndex output
        tickers = ["AAPL", "MSFT"]
        mock_dl.return_value = _make_multi_ticker_data(tickers)

        # Act
        result = batch_download_history(tickers)

        # Assert — both tickers extracted
        assert set(result.keys()) == {"AAPL", "MSFT"}
        assert "Close" in result["AAPL"].columns
        assert "Close" in result["MSFT"].columns

    @patch("infrastructure.market_data.market_data._rate_limiter")
    @patch("infrastructure.market_data.market_data.yf.download")
    def test_should_skip_ticker_missing_from_download_result(self, mock_dl, _mock_rl):
        # Arrange — AAPL present, MSFT causes KeyError
        data = _make_multi_ticker_data(["AAPL"])
        mock_dl.return_value = data

        # Act — MSFT will raise KeyError inside the loop, should be silently skipped
        result = batch_download_history(["AAPL", "MSFT"])

        # Assert — only AAPL present (or empty if AAPL also fails on missing MSFT slice)
        assert "MSFT" not in result


# ===========================================================================
# prime_signals_cache_batch
# ===========================================================================


class TestPrimeSignalsCacheBatchSkip:
    """prime_signals_cache_batch should skip tickers already in L1 cache."""

    @patch("infrastructure.market_data.market_data._fetch_signals_from_yf")
    def test_should_skip_ticker_already_in_l1_cache(self, mock_fetch):
        # Arrange — AAPL already in L1
        l1 = _fresh_signals_l1()
        l1["AAPL"] = {"ticker": "AAPL", "price": 200.0, "rsi": 55.0}
        hist_map = {"AAPL": _make_hist()}

        with patch("infrastructure.market_data.market_data._signals_cache", l1):
            # Act
            primed = prime_signals_cache_batch(hist_map)

        # Assert — fetcher never called, count = 0
        assert primed == 0
        mock_fetch.assert_not_called()

    @patch("infrastructure.market_data.market_data._fetch_signals_from_yf")
    def test_should_return_zero_when_all_tickers_already_cached(self, mock_fetch):
        # Arrange — two tickers, both cached
        l1 = _fresh_signals_l1()
        l1["AAPL"] = {"ticker": "AAPL", "price": 200.0}
        l1["MSFT"] = {"ticker": "MSFT", "price": 400.0}
        hist_map = {"AAPL": _make_hist(), "MSFT": _make_hist()}

        with patch("infrastructure.market_data.market_data._signals_cache", l1):
            primed = prime_signals_cache_batch(hist_map)

        assert primed == 0
        mock_fetch.assert_not_called()


class TestPrimeSignalsCacheBatchWrite:
    """prime_signals_cache_batch should write successful results to L1 only (not L2).

    Prewarm results intentionally omit institutional_holders (no extra yf.Ticker() call).
    Writing to L2 (1hr TTL) would lock in that incomplete data. Instead, only L1 (5min)
    is warmed; the first L1 miss after expiry triggers a full fetch that populates L2.
    """

    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_signals_from_yf")
    def test_should_write_success_result_to_l1_only_not_l2(
        self, mock_fetch, mock_disk_set
    ):
        # Arrange — L1 empty, fetcher returns valid signals
        signals = {"ticker": "AAPL", "price": 200.0, "rsi": 55.0}
        mock_fetch.return_value = signals
        l1 = _fresh_signals_l1()
        hist_map = {"AAPL": _make_hist()}

        with patch("infrastructure.market_data.market_data._signals_cache", l1):
            # Act
            primed = prime_signals_cache_batch(hist_map)

        # Assert — L1 is warmed, L2 (disk) is intentionally NOT written during prewarm
        assert primed == 1
        assert l1.get("AAPL") == signals
        mock_disk_set.assert_not_called()

    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_signals_from_yf")
    def test_should_not_write_error_result_to_l2(self, mock_fetch, mock_disk_set):
        # Arrange — fetcher returns error dict
        error_result = {"error": "市場資料取得失敗"}
        mock_fetch.return_value = error_result
        l1 = _fresh_signals_l1()
        hist_map = {"AAPL": _make_hist()}

        with patch("infrastructure.market_data.market_data._signals_cache", l1):
            # Act
            primed = prime_signals_cache_batch(hist_map)

        # Assert — L1 gets the error entry (short-lived), L2 skipped
        assert primed == 1  # counted as primed (wrote to L1)
        assert l1.get("AAPL") == error_result
        mock_disk_set.assert_not_called()

    @patch("infrastructure.market_data.market_data._disk_set")
    @patch("infrastructure.market_data.market_data._fetch_signals_from_yf")
    def test_should_return_count_of_primed_tickers(self, mock_fetch, mock_disk_set):
        # Arrange — three tickers, all miss L1
        mock_fetch.return_value = {"ticker": "X", "price": 100.0, "rsi": 50.0}
        l1 = _fresh_signals_l1()
        hist_map = {
            "AAPL": _make_hist(),
            "MSFT": _make_hist(),
            "GOOGL": _make_hist(),
        }

        with patch("infrastructure.market_data.market_data._signals_cache", l1):
            primed = prime_signals_cache_batch(hist_map)

        # Assert — all three primed
        assert primed == 3

    @patch("infrastructure.market_data.market_data._fetch_signals_from_yf")
    def test_should_pass_pre_fetched_hist_to_fetch_signals(self, mock_fetch):
        # Arrange — verify the hist is forwarded as pre_fetched_hist kwarg
        signals = {"ticker": "AAPL", "price": 200.0, "rsi": 55.0}
        mock_fetch.return_value = signals
        hist = _make_hist()
        l1 = _fresh_signals_l1()

        with (
            patch("infrastructure.market_data.market_data._signals_cache", l1),
            patch("infrastructure.market_data.market_data._disk_set"),
        ):
            prime_signals_cache_batch({"AAPL": hist})

        # Assert — pre_fetched_hist was passed
        mock_fetch.assert_called_once_with("AAPL", pre_fetched_hist=hist)
