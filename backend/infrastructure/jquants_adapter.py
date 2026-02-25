"""Backward-compatibility shim — re-exports infrastructure.market_data.jquants_adapter.

Consumers using ``import infrastructure.jquants_adapter`` continue to work unchanged.
"""

from infrastructure.market_data.jquants_adapter import (  # noqa: F401
    get_financials,
    is_available,
)
