"""Backward-compatibility shim — re-exports domain.portfolio.stress_test.

Consumers using ``from domain.stress_test import X`` continue to work unchanged.
"""

from domain.portfolio.stress_test import (  # noqa: F401
    calculate_portfolio_beta,
    calculate_stress_test,
    classify_pain_level,
    generate_advice,
)
