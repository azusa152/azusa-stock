"""Backward-compatibility shim — re-exports infrastructure.market_data.market_data_resolver.

Consumers using ``from infrastructure.market_data_resolver import X`` continue to work unchanged.
"""

from infrastructure.market_data.market_data_resolver import (  # noqa: F401
    MarketDataResolver,
    _infer_market,
    _is_jp_ticker,
    _is_tw_ticker,
)
