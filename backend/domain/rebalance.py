"""Backward-compatibility shim — re-exports domain.portfolio.rebalance.

Consumers using ``from domain.rebalance import X`` continue to work unchanged.
"""

from domain.portfolio.rebalance import (  # noqa: F401
    calculate_rebalance,
    compute_portfolio_health_score,
)
