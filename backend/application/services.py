"""
Application — Service Layer (Use Cases) — 相容性 facade。
所有業務邏輯已遷移至各專門 service 模組，此檔案提供向後相容的 re-export。

實際實作：
  - application.stock_service     → 股票 CRUD、觀點、匯入匯出、護城河
  - application.scan_service      → 三層掃描、價格警報、掃描歷史
  - application.rebalance_service → 再平衡、匯率曝險、X-Ray、FX 警報
  - application.webhook_service   → OpenClaw webhook 處理
  - application.notification_service → 每週摘要、投資組合摘要
"""

# ---------------------------------------------------------------------------
# Stock Service (CRUD, thesis, import/export, moat)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Notification Service (weekly digest, portfolio summary)
# ---------------------------------------------------------------------------
from application.messaging.notification_service import (  # noqa: F401
    get_portfolio_summary,
    send_weekly_digest,
)

# ---------------------------------------------------------------------------
# Webhook Service
# ---------------------------------------------------------------------------
from application.messaging.webhook_service import handle_webhook  # noqa: F401

# ---------------------------------------------------------------------------
# Rebalance Service (rebalance, currency exposure, X-Ray, FX alerts)
# ---------------------------------------------------------------------------
from application.portfolio.rebalance_service import (  # noqa: F401
    _compute_holding_market_values,
    calculate_currency_exposure,
    calculate_rebalance,
    calculate_withdrawal,
    check_fx_alerts,
    send_fx_alerts,
    send_xray_warnings,
)

# ---------------------------------------------------------------------------
# Stress Test Service (portfolio stress testing)
# ---------------------------------------------------------------------------
from application.portfolio.stress_test_service import (
    calculate_stress_test,  # noqa: F401
)

# ---------------------------------------------------------------------------
# Scan Service (scanning, price alerts, scan history)
# ---------------------------------------------------------------------------
from application.scan.scan_service import (  # noqa: F401
    create_price_alert,
    delete_price_alert,
    get_latest_scan_logs,
    get_scan_history,
    list_price_alerts,
    run_scan,
)
from application.stock.stock_service import (  # noqa: F401
    CategoryUnchangedError,
    StockAlreadyActiveError,
    StockAlreadyExistsError,
    StockAlreadyInactiveError,
    StockNotFoundError,
    _append_thesis_log,
    _get_stock_or_raise,
    _str_to_tags,
    _tags_to_str,
    add_thesis,
    create_stock,
    deactivate_stock,
    export_stocks,
    get_enriched_stocks,
    get_moat_for_ticker,
    get_removal_history,
    get_thesis_history,
    import_stocks,
    list_active_stocks,
    list_removed_stocks,
    reactivate_stock,
    update_display_order,
    update_stock_category,
)
