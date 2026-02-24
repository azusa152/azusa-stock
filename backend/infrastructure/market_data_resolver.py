from typing import Optional

from domain.enums import MoatStatus
from logging_config import get_logger

logger = get_logger(__name__)

_MOAT_NOT_AVAILABLE = MoatStatus.NOT_AVAILABLE.value


def _is_jp_ticker(ticker: str) -> bool:
    return ticker.endswith(".T")


def _is_tw_ticker(ticker: str) -> bool:
    return ticker.endswith(".TW")


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
        from infrastructure import market_data as yf

        self._yf = yf

        try:
            from infrastructure import jquants_adapter

            if jquants_adapter.is_available():
                self._jquants = jquants_adapter
                logger.info("J-Quants adapter 已啟用")
            else:
                self._jquants = None
        except ImportError:
            self._jquants = None

    def get_technical_signals(self, ticker: str) -> Optional[dict]:
        return self._yf.get_technical_signals(ticker)

    def get_price_history(self, ticker: str) -> Optional[list[dict]]:
        return self._yf.get_price_history(ticker)

    def get_earnings_date(self, ticker: str) -> Optional[str]:
        return self._yf.get_earnings_date(ticker)

    def get_dividend_info(self, ticker: str) -> Optional[dict]:
        return self._yf.get_dividend_info(ticker)

    def analyze_moat_trend(self, ticker: str) -> dict:
        result = self._yf.analyze_moat_trend(ticker)

        # If yfinance returned NOT_AVAILABLE for a JP ticker, try J-Quants
        if (
            _is_jp_ticker(ticker)
            and result.get("moat") == _MOAT_NOT_AVAILABLE
            and self._jquants is not None
            and self._jquants.is_available()
        ):
            logger.info("%s yfinance 護城河資料不足，嘗試 J-Quants 補充", ticker)
            jq_data = self._jquants.get_financials(ticker)
            if jq_data and jq_data.get("gross_profit") and jq_data.get("revenue"):
                # Recalculate margin from J-Quants data
                margin = round(
                    float(jq_data["gross_profit"]) / float(jq_data["revenue"]) * 100,
                    2,
                )
                result["current_margin"] = margin
                result["moat"] = "STABLE"  # Have data = at least stable
                result["details"] = f"Margin {margin:.1f}% (via J-Quants)"
                result["source"] = "jquants"

        return result

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
