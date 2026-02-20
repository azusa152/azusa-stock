"""
Tests for sector cache functions (get_ticker_sector_cached).

Covers:
- Cache hit returns sector name.
- Cache miss (no entry) returns None without network call.
- Sentinel _SECTOR_NOT_FOUND in cache returns None.
- Empty ticker returns None.
"""

import os
import tempfile

os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants  # noqa: E402

domain.constants.DISK_CACHE_DIR = os.path.join(
    tempfile.gettempdir(), "folio_test_cache_sector"
)

from unittest.mock import patch  # noqa: E402

from infrastructure.market_data import (  # noqa: E402
    _SECTOR_NOT_FOUND,
    _disk_set,
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
