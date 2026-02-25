"""
Optional J-Quants API adapter for Japanese stock financial data.
Activated only when JQUANTS_API_KEY env var is set.
"""

import os
from typing import Optional

from logging_config import get_logger

logger = get_logger(__name__)

_client = None


def _get_client():
    """Lazy-init J-Quants client. Returns None if API key not configured."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("JQUANTS_API_KEY")
    if not api_key:
        return None

    try:
        import jquantsapi

        _client = jquantsapi.Client(refresh_token=api_key)
        logger.info("J-Quants API 客戶端初始化成功")
        return _client
    except Exception as e:
        logger.warning("J-Quants API 初始化失敗：%s", e)
        return None


def is_available() -> bool:
    return _get_client() is not None


def get_financials(ticker_code: str) -> Optional[dict]:
    """
    Fetch financial statements for a JP ticker from J-Quants.
    ticker_code: 4-digit JP code (e.g. "7203"), NOT the yfinance suffix form.
    Returns dict with gross_profit, revenue, or None on failure.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        # J-Quants uses 5-digit codes (4 digits + 0 suffix)
        code = ticker_code.replace(".T", "") + "0"
        statements = client.get_statements_range(
            code=code,
        )
        if statements is None or statements.empty:
            logger.warning("J-Quants %s 無財報資料", ticker_code)
            return None

        # Extract latest quarter gross margin data
        # J-Quants returns columns: GrossProfit, NetSales, etc.
        latest = statements.iloc[0]
        result = {
            "gross_profit": latest.get("GrossProfit"),
            "revenue": latest.get("NetSales") or latest.get("OperatingRevenue"),
        }
        logger.info("J-Quants %s 財報取得成功", ticker_code)
        return result

    except Exception as e:
        logger.warning("J-Quants %s 財報取得失敗：%s", ticker_code, e)
        return None
