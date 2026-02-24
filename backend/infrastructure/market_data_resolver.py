from typing import Optional

from logging_config import get_logger

logger = get_logger(__name__)


def _is_jp_ticker(ticker: str) -> bool:
    return ticker.endswith(".T")


def _infer_market(ticker: str) -> str:
    if ticker.endswith(".T"):
        return "JP"
    if ticker.endswith(".TW"):
        return "TW"
    if ticker.endswith(".HK"):
        return "HK"
    return "US"


class MarketDataResolver:
    """
    Routes market data requests to the appropriate provider.
    Phase 4: single provider (yfinance). Phase 5 adds J-Quants fallback.
    """

    def __init__(self):
        # Lazy import to avoid circular dependency at module level
        from infrastructure import market_data as yf

        self._yf = yf
        self._jquants = None  # Phase 5

    def get_technical_signals(self, ticker: str) -> Optional[dict]:
        return self._yf.get_technical_signals(ticker)

    def get_price_history(self, ticker: str) -> Optional[list[dict]]:
        return self._yf.get_price_history(ticker)

    def get_earnings_date(self, ticker: str) -> Optional[str]:
        return self._yf.get_earnings_date(ticker)

    def get_dividend_info(self, ticker: str) -> Optional[dict]:
        return self._yf.get_dividend_info(ticker)

    def analyze_moat_trend(self, ticker: str) -> dict:
        return self._yf.analyze_moat_trend(ticker)

    def get_stock_beta(self, ticker: str) -> Optional[float]:
        return self._yf.get_stock_beta(ticker)

    def get_ticker_sector(self, ticker: str) -> Optional[str]:
        return self._yf.get_ticker_sector(ticker)

    def get_exchange_rate(self, display_cur: str, holding_cur: str) -> float:
        return self._yf.get_exchange_rate(display_cur, holding_cur)

    def get_exchange_rates(
        self, display_cur: str, holding_currencies: list[str]
    ) -> dict[str, float]:
        return self._yf.get_exchange_rates(display_cur, holding_currencies)
