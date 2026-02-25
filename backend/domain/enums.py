"""Backward-compatibility shim — re-exports domain.core.enums.

Consumers using ``from domain.enums import X`` continue to work unchanged.
"""

from domain.core.enums import (  # noqa: F401
    CATEGORY_LABEL,
    FEAR_GREED_LABEL,
    FX_ALERT_LABEL,
    FXAlertType,
    FearGreedLevel,
    HoldingAction,
    MarketSentiment,
    MoatStatus,
    ScanSignal,
    StockCategory,
)
