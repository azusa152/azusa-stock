"""
Optional FinMind API adapter for Taiwan stock financial data.
Activated only when FINMIND_API_TOKEN env var is set.
Includes a circuit breaker: after 3 consecutive failures, disables for 30 minutes.
"""

import os
import time
from datetime import date, timedelta

import requests

from logging_config import get_logger

logger = get_logger(__name__)

FINMIND_API_URL = "https://api.finmindtrade.com/api/v4/data"
_CIRCUIT_BREAKER_THRESHOLD = 3
_CIRCUIT_BREAKER_COOLDOWN = 1800  # 30 minutes in seconds

_consecutive_failures = 0
_circuit_open_until: float = 0


def _get_token() -> str | None:
    return os.getenv("FINMIND_API_TOKEN") or None


def is_available() -> bool:
    """Returns True if token is set and circuit breaker is not open."""
    if not _get_token():
        return False
    if time.time() < _circuit_open_until:
        logger.debug(
            "FinMind circuit breaker open, skipping (source=finmind, market=TW)"
        )
        return False
    return True


def _latest_value(rows: list[dict], type_name: str) -> float | None:
    """Return the value from the most recent row matching the given type."""
    matching = sorted(
        [r for r in rows if r.get("type") == type_name],
        key=lambda r: r.get("date", ""),
        reverse=True,
    )
    if not matching:
        return None
    try:
        return float(matching[0]["value"])
    except (KeyError, TypeError, ValueError):
        return None


def get_financials(ticker_code: str) -> dict | None:
    """
    Fetch financial statements for a TW ticker from FinMind.
    ticker_code: yfinance-style TW ticker (e.g. "2330.TW").
    Returns dict with gross_profit, revenue, or None on failure.
    """
    global _consecutive_failures, _circuit_open_until

    token = _get_token()
    if not token:
        return None

    if time.time() < _circuit_open_until:
        logger.debug(
            "FinMind circuit breaker open, skipping %s (source=finmind, market=TW)",
            ticker_code,
        )
        return None

    code = ticker_code.replace(".TW", "")
    params = {
        "dataset": "TaiwanStockFinancialStatements",
        "data_id": code,
        "start_date": (date.today() - timedelta(days=365)).isoformat(),
        "token": token,
    }

    try:
        resp = requests.get(FINMIND_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        rows = resp.json().get("data", [])

        gross_profit = _latest_value(rows, "GrossProfit")
        revenue = _latest_value(rows, "Revenue")

        if gross_profit is None and revenue is None:
            # 200 OK but no useful financial data — don't count as success or failure
            logger.warning(
                "FinMind %s 無有效財報資料 (source=finmind, market=TW)", ticker_code
            )
            return None

        _consecutive_failures = 0  # reset on success
        result = {"gross_profit": gross_profit, "revenue": revenue}
        logger.info("FinMind %s 財報取得成功 (source=finmind, market=TW)", ticker_code)
        return result

    except Exception as e:
        _consecutive_failures += 1
        if _consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
            _circuit_open_until = time.time() + _CIRCUIT_BREAKER_COOLDOWN
            logger.warning(
                "FinMind circuit breaker opened after %d failures (source=finmind, market=TW)",
                _consecutive_failures,
            )
        else:
            logger.warning(
                "FinMind %s 財報取得失敗 (source=finmind, market=TW, failures=%d)：%s",
                ticker_code,
                _consecutive_failures,
                e,
            )
        return None
