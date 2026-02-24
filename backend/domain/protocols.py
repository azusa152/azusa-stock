from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class MarketDataProvider(Protocol):
    """Interface for market data providers (yfinance, J-Quants, etc.)."""

    def get_technical_signals(self, ticker: str) -> Optional[dict]:
        """RSI, MA200, MA60, bias, volume ratio, daily change."""
        ...

    def get_price_history(self, ticker: str) -> Optional[list[dict]]:
        """1-year close price history."""
        ...

    def get_earnings_date(self, ticker: str) -> Optional[str]:
        """Next earnings date."""
        ...

    def get_dividend_info(self, ticker: str) -> Optional[dict]:
        """Dividend yield and YTD dividend."""
        ...

    def analyze_moat_trend(self, ticker: str) -> dict:
        """Gross margin YoY analysis."""
        ...

    def get_stock_beta(self, ticker: str) -> Optional[float]:
        """Stock beta."""
        ...

    def get_ticker_sector(self, ticker: str) -> Optional[str]:
        """GICS sector."""
        ...
