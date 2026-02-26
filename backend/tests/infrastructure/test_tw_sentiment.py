import math
from unittest.mock import patch

import pandas as pd
import pytest

from infrastructure.market_data.market_data import get_tw_volatility_index


def _make_hist(prices: list[float]) -> pd.DataFrame:
    """Build a minimal yfinance-style history DataFrame with a Close column."""
    return pd.DataFrame({"Close": prices})


# ---------------------------------------------------------------------------
# Vol calculation correctness
# ---------------------------------------------------------------------------


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_returns_value_and_level(mock_hist):
    """Returns a dict with value, level, and source for valid history."""
    # Use a flat price series with slight noise to produce a known vol (≥15 prices)
    prices = [
        100.0,
        101.0,
        99.5,
        100.5,
        100.0,
        101.5,
        100.0,
        99.0,
        101.0,
        100.5,
        100.2,
        100.8,
        99.7,
        101.1,
        100.3,
    ]
    mock_hist.return_value = _make_hist(prices)

    result = get_tw_volatility_index()

    assert result is not None
    assert "value" in result
    assert "level" in result
    assert result["source"] == "TAIEX Realized Vol"
    assert isinstance(result["value"], float)
    assert result["value"] > 0


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_vol_calculation_matches_formula(mock_hist):
    """Annualized vol matches std(log_returns) * sqrt(252) * 100."""
    prices = [
        100.0,
        102.0,
        98.0,
        105.0,
        100.0,
        103.0,
        97.0,
        101.0,
        99.0,
        104.0,
        101.5,
        98.5,
        103.0,
        100.0,
        102.5,
    ]
    mock_hist.return_value = _make_hist(prices)

    result = get_tw_volatility_index()
    assert result is not None

    # Manually compute expected vol
    s = pd.Series(prices)
    log_returns = (s / s.shift(1)).apply(math.log).dropna()
    expected_vol = round(float(log_returns.std() * math.sqrt(252) * 100), 2)

    assert result["value"] == pytest.approx(expected_vol, rel=1e-4)


# ---------------------------------------------------------------------------
# Fear/greed level mapping
# ---------------------------------------------------------------------------


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_extreme_fear_level(mock_hist):
    """Annualized vol > 30% → EXTREME_FEAR."""
    # Large daily swings → high vol
    prices = [100, 120, 90, 130, 80, 125, 85, 135, 75, 140, 70, 145, 65, 150, 60, 155]
    mock_hist.return_value = _make_hist(prices)

    result = get_tw_volatility_index()
    assert result is not None
    assert result["level"] == "EXTREME_FEAR"


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_extreme_greed_level(mock_hist):
    """Annualized vol < 10% → EXTREME_GREED."""
    # Tiny daily changes → very low vol
    prices = [100.0 + i * 0.001 for i in range(30)]
    mock_hist.return_value = _make_hist(prices)

    result = get_tw_volatility_index()
    assert result is not None
    assert result["level"] == "EXTREME_GREED"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_returns_none_when_empty(mock_hist):
    """Returns None when history is empty."""
    mock_hist.return_value = pd.DataFrame()

    result = get_tw_volatility_index()
    assert result is None


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_returns_none_when_insufficient_data(mock_hist):
    """Returns None when fewer than 15 closes are available."""
    mock_hist.return_value = _make_hist([100.0, 101.0, 99.0, 100.5])

    result = get_tw_volatility_index()
    assert result is None


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_returns_none_when_history_is_none(mock_hist):
    """Returns None gracefully when _yf_history_short returns None."""
    mock_hist.return_value = None

    result = get_tw_volatility_index()
    assert result is None


@patch("infrastructure.market_data.market_data._yf_history_short")
def test_returns_none_on_exception(mock_hist):
    """Returns None and does not raise when an unexpected error occurs."""
    mock_hist.side_effect = RuntimeError("network error")

    result = get_tw_volatility_index()
    assert result is None
