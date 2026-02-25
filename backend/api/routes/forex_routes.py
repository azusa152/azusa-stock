"""
Forex Exchange Rate API Routes
Exposes FX historical data for frontend chart visualization.
"""

from fastapi import APIRouter

from application.portfolio.fx_watch_service import get_forex_history

router = APIRouter(prefix="/forex", tags=["Forex"])


@router.get("/{base}/{quote}/history-long")
def get_forex_history_endpoint(base: str, quote: str) -> list[dict]:
    """
    Get 3-month daily FX rate history for a currency pair.

    Args:
        base: Base currency code (e.g., 'USD')
        quote: Quote currency code (e.g., 'TWD')

    Returns:
        List of daily rate records: [{"date": "YYYY-MM-DD", "close": 32.15}, ...]

    Cache:
        - L1 (in-memory): 2 hours
        - L2 (disk): 4 hours
    """
    return get_forex_history(base, quote)
