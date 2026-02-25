"""Backward-compatibility shim — re-exports domain.analysis.smart_money.

Consumers using ``from domain.smart_money import X`` continue to work unchanged.
"""

from domain.analysis.smart_money import (  # noqa: F401
    classify_holding_change,
    compute_change_pct,
    compute_holding_weight,
    compute_resonance_matches,
)
