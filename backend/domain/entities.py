"""Backward-compatibility shim — re-exports domain.core.entities.

Consumers using ``from domain.entities import X`` continue to work unchanged.
"""

from domain.core.entities import (  # noqa: F401
    FXWatchConfig,
    Guru,
    GuruFiling,
    GuruHolding,
    Holding,
    NetWorthItem,
    NetWorthSnapshot,
    NotificationLog,
    PortfolioSnapshot,
    PriceAlert,
    RemovalLog,
    ScanLog,
    Stock,
    SystemTemplate,
    ThesisLog,
    UserInvestmentProfile,
    UserPreferences,
    UserTelegramSettings,
)
