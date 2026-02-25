from unittest.mock import MagicMock, patch

from domain.enums import MoatStatus
from domain.protocols import MarketDataProvider
from infrastructure.market_data.market_data_resolver import (
    MarketDataResolver,
    _is_tw_ticker,
)

NOT_AVAILABLE = MoatStatus.NOT_AVAILABLE.value


def test_resolver_satisfies_protocol():
    """MarketDataResolver structurally conforms to MarketDataProvider."""
    resolver = MarketDataResolver()
    assert isinstance(resolver, MarketDataProvider)


@patch("infrastructure.market_data.market_data.analyze_moat_trend")
def test_jp_moat_fallback_to_jquants(mock_yf_moat):
    """When yfinance returns NOT_AVAILABLE for a JP ticker, tries J-Quants."""
    mock_yf_moat.return_value = {"moat": NOT_AVAILABLE, "ticker": "7203.T"}

    mock_jquants = MagicMock()
    mock_jquants.is_available.return_value = True
    mock_jquants.get_financials.return_value = {
        "gross_profit": 3000000,
        "revenue": 10000000,
    }

    resolver = MarketDataResolver()
    resolver._jquants = mock_jquants

    result = resolver.analyze_moat_trend("7203.T")

    mock_jquants.get_financials.assert_called_once_with("7203.T")
    assert result["moat"] == "STABLE"
    assert result["current_margin"] == 30.0
    assert result["source"] == "jquants"


@patch("infrastructure.market_data.market_data.analyze_moat_trend")
def test_non_jp_ticker_never_calls_jquants(mock_yf_moat):
    """Non-JP tickers never touch J-Quants even if it is available."""
    mock_yf_moat.return_value = {"moat": NOT_AVAILABLE, "ticker": "AAPL"}

    mock_jquants = MagicMock()
    mock_jquants.is_available.return_value = True

    resolver = MarketDataResolver()
    resolver._jquants = mock_jquants

    resolver.analyze_moat_trend("AAPL")

    mock_jquants.get_financials.assert_not_called()


def test_is_tw_ticker():
    assert _is_tw_ticker("2330.TW") is True
    assert _is_tw_ticker("2317.TW") is True
    assert _is_tw_ticker("7203.T") is False
    assert _is_tw_ticker("AAPL") is False
    assert _is_tw_ticker("0700.HK") is False


@patch("infrastructure.market_data.market_data.analyze_moat_trend")
def test_tw_moat_fallback_to_finmind(mock_yf_moat):
    """When yfinance returns NOT_AVAILABLE for a TW ticker, tries FinMind."""
    mock_yf_moat.return_value = {"moat": NOT_AVAILABLE, "ticker": "2330.TW"}

    mock_finmind = MagicMock()
    mock_finmind.is_available.return_value = True
    mock_finmind.get_financials.return_value = {
        "gross_profit": 250000,
        "revenue": 1000000,
    }

    resolver = MarketDataResolver()
    resolver._finmind = mock_finmind

    result = resolver.analyze_moat_trend("2330.TW")

    mock_finmind.get_financials.assert_called_once_with("2330.TW")
    assert result["moat"] == "STABLE"
    assert result["current_margin"] == 25.0
    assert result["source"] == "finmind"


@patch("infrastructure.market_data.market_data.analyze_moat_trend")
def test_non_tw_ticker_never_calls_finmind(mock_yf_moat):
    """Non-TW tickers never touch FinMind even if it is available."""
    mock_yf_moat.return_value = {"moat": NOT_AVAILABLE, "ticker": "AAPL"}

    mock_finmind = MagicMock()
    mock_finmind.is_available.return_value = True

    resolver = MarketDataResolver()
    resolver._finmind = mock_finmind

    resolver.analyze_moat_trend("AAPL")

    mock_finmind.get_financials.assert_not_called()


@patch("infrastructure.market_data.market_data.analyze_moat_trend")
def test_tw_moat_skips_finmind_when_yfinance_succeeds(mock_yf_moat):
    """When yfinance returns a non-N/A moat for a TW ticker, FinMind is not called."""
    mock_yf_moat.return_value = {"moat": "STABLE", "ticker": "2330.TW"}

    mock_finmind = MagicMock()
    mock_finmind.is_available.return_value = True

    resolver = MarketDataResolver()
    resolver._finmind = mock_finmind

    result = resolver.analyze_moat_trend("2330.TW")

    mock_finmind.get_financials.assert_not_called()
    assert result["moat"] == "STABLE"


@patch("infrastructure.market_data.market_data.analyze_moat_trend")
def test_jp_moat_skips_jquants_when_yfinance_succeeds(mock_yf_moat):
    """When yfinance returns a non-N/A moat, J-Quants is not called."""
    mock_yf_moat.return_value = {"moat": "STABLE", "ticker": "7203.T"}

    mock_jquants = MagicMock()
    mock_jquants.is_available.return_value = True

    resolver = MarketDataResolver()
    resolver._jquants = mock_jquants

    result = resolver.analyze_moat_trend("7203.T")

    mock_jquants.get_financials.assert_not_called()
    assert result["moat"] == "STABLE"
