"""application.portfolio sub-package — re-exports public API for backward compatibility."""

from application.portfolio.fx_watch_service import (  # noqa: F401
    check_fx_watches,
    create_watch,
    get_all_watches,
    get_forex_history,
    remove_watch,
    send_fx_watch_alerts,
    update_watch,
)
from application.portfolio.holding_service import (  # noqa: F401
    create_cash_holding,
    create_holding,
    delete_holding,
    export_holdings,
    import_holdings,
    list_holdings,
    update_holding,
)
from application.portfolio.rebalance_service import (  # noqa: F401
    _compute_holding_market_values,
    calculate_currency_exposure,
    calculate_rebalance,
    calculate_withdrawal,
    check_fx_alerts,
    send_fx_alerts,
    send_xray_warnings,
)
from application.portfolio.snapshot_service import (  # noqa: F401
    get_snapshot_range,
    get_snapshots,
    take_daily_snapshot,
)
from application.portfolio.stress_test_service import (  # noqa: F401
    calculate_stress_test,
)
