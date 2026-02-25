"""Backward-compatibility shim — re-exports domain.core.protocols.

Consumers using ``from domain.protocols import MarketDataProvider`` continue to work unchanged.
"""

from domain.core.protocols import MarketDataProvider  # noqa: F401
