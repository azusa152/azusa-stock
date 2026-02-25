"""Backward-compatibility shim — re-exports domain.analysis.fx_analysis.

Consumers using ``from domain.fx_analysis import X`` continue to work unchanged.
"""

from domain.analysis.fx_analysis import (  # noqa: F401
    FXRateAlert,
    FXTimingResult,
    analyze_fx_rate_changes,
    assess_exchange_timing,
    count_consecutive_increases,
    determine_fx_risk_level,
    is_recent_high,
)
