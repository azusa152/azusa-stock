"""Tests for daily change calculation in market_data."""

import os
import tempfile

os.environ.setdefault("LOG_DIR", os.path.join(tempfile.gettempdir(), "folio_test_logs"))
os.environ.setdefault("DATABASE_URL", "sqlite://")

import domain.constants

domain.constants.DISK_CACHE_DIR = os.path.join(tempfile.gettempdir(), "folio_test_cache_change")

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from infrastructure.market_data import _fetch_signals_from_yf


class TestDailyChangeCalculation:
    """Tests for daily change (previous_close, change_pct) calculation."""

    @patch("infrastructure.market_data._yf_history")
    def test_fetch_signals_should_include_change_when_sufficient_history(self, mock_yf):
        # Arrange: Need at least MIN_HISTORY_DAYS_FOR_SIGNALS (60) data points
        mock_stock = MagicMock()
        # Generate 65 days of data with gradual increase, last 2 days: 115 -> 120
        closes = [100.0 + (i * 0.25) for i in range(63)] + [115.0, 120.0]
        mock_hist = pd.DataFrame(
            {
                "Close": closes,
                "Volume": [1000] * 65,
            }
        )
        mock_yf.return_value = (mock_stock, mock_hist)

        # Act
        result = _fetch_signals_from_yf("NVDA")

        # Assert
        assert result["price"] == 120.0
        assert result["previous_close"] == 115.0
        assert result["change_pct"] == pytest.approx(4.35, rel=0.01)  # (120-115)/115*100

    @patch("infrastructure.market_data._yf_history")
    def test_fetch_signals_should_return_none_change_when_insufficient_history(self, mock_yf):
        # Arrange: Only 1 day of history
        mock_stock = MagicMock()
        mock_hist = pd.DataFrame(
            {
                "Close": [120.0],
                "Volume": [1000],
            }
        )
        mock_yf.return_value = (mock_stock, mock_hist)

        # Act
        result = _fetch_signals_from_yf("NVDA")

        # Assert
        assert result["price"] == 120.0
        assert result["previous_close"] is None
        assert result["change_pct"] is None

    @patch("infrastructure.market_data._yf_history")
    def test_fetch_signals_should_handle_zero_previous_close(self, mock_yf):
        # Arrange: Previous close is 0 (edge case), need 60+ data points
        mock_stock = MagicMock()
        # Generate 60 days with last two being 0.0, 120.0
        closes = [100.0 + (i * 0.25) for i in range(58)] + [0.0, 120.0]
        mock_hist = pd.DataFrame(
            {
                "Close": closes,
                "Volume": [1000] * 60,
            }
        )
        mock_yf.return_value = (mock_stock, mock_hist)

        # Act
        result = _fetch_signals_from_yf("NVDA")

        # Assert
        assert result["price"] == 120.0
        assert result["previous_close"] == 0.0
        assert result["change_pct"] is None  # Should not calculate with 0 divisor

    @patch("infrastructure.market_data._yf_history")
    def test_fetch_signals_should_calculate_positive_change(self, mock_yf):
        # Arrange: Price increased, need 60+ data points
        mock_stock = MagicMock()
        # Generate 60 days with last two being 100.0, 110.0
        closes = [95.0 + (i * 0.1) for i in range(58)] + [100.0, 110.0]
        mock_hist = pd.DataFrame(
            {
                "Close": closes,
                "Volume": [1000] * 60,
            }
        )
        mock_yf.return_value = (mock_stock, mock_hist)

        # Act
        result = _fetch_signals_from_yf("NVDA")

        # Assert
        assert result["change_pct"] == pytest.approx(10.0, rel=0.01)  # (110-100)/100*100

    @patch("infrastructure.market_data._yf_history")
    def test_fetch_signals_should_calculate_negative_change(self, mock_yf):
        # Arrange: Price decreased, need 60+ data points
        mock_stock = MagicMock()
        # Generate 60 days with last two being 110.0, 100.0
        closes = [105.0 + (i * 0.1) for i in range(58)] + [110.0, 100.0]
        mock_hist = pd.DataFrame(
            {
                "Close": closes,
                "Volume": [1000] * 60,
            }
        )
        mock_yf.return_value = (mock_stock, mock_hist)

        # Act
        result = _fetch_signals_from_yf("NVDA")

        # Assert
        assert result["change_pct"] == pytest.approx(-9.09, rel=0.01)  # (100-110)/110*100

    @patch("infrastructure.market_data._yf_history")
    def test_fetch_signals_should_round_change_to_two_decimals(self, mock_yf):
        # Arrange: Change results in many decimals, need 60+ data points
        mock_stock = MagicMock()
        # Generate 60 days with last two being 123.456, 125.789
        closes = [120.0 + (i * 0.05) for i in range(58)] + [123.456, 125.789]
        mock_hist = pd.DataFrame(
            {
                "Close": closes,
                "Volume": [1000] * 60,
            }
        )
        mock_yf.return_value = (mock_stock, mock_hist)

        # Act
        result = _fetch_signals_from_yf("NVDA")

        # Assert
        assert result["previous_close"] == 123.46  # Rounded to 2 decimals
        assert result["change_pct"] == 1.89  # Rounded to 2 decimals
        assert isinstance(result["change_pct"], float)
