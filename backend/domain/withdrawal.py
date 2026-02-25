"""Backward-compatibility shim — re-exports domain.portfolio.withdrawal.

Consumers using ``from domain.withdrawal import X`` continue to work unchanged.
"""

from domain.portfolio.withdrawal import (  # noqa: F401
    HoldingData,
    SellRecommendation,
    WithdrawalPlan,
    plan_withdrawal,
)
