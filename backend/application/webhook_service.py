"""
Application — Webhook Service：OpenClaw / AI agent webhook 處理。
"""

from sqlmodel import Session

from application.formatters import format_fear_greed_label
from application.stock_service import (
    StockAlreadyExistsError,
    StockNotFoundError,
    create_stock,
)
from application.scan_service import list_price_alerts, run_scan
from application.notification_service import get_portfolio_summary
from domain.constants import (
    DEFAULT_IMPORT_CATEGORY,
    DEFAULT_WEBHOOK_THESIS,
    WEBHOOK_ACTION_REGISTRY,
    WEBHOOK_MISSING_TICKER,
)
from domain.enums import StockCategory
from infrastructure.market_data import (
    analyze_moat_trend,
    get_fear_greed_index,
    get_technical_signals,
)
from logging_config import get_logger

logger = get_logger(__name__)


def handle_webhook(session: Session, action: str, ticker: str | None, params: dict) -> dict:
    """
    處理 AI agent webhook 請求。回傳 dict(success, message, data)。
    業務邏輯集中於此，API handler 只負責 parse + 回傳。
    """
    import threading as _threading

    action = action.lower().strip()
    ticker = ticker.upper().strip() if ticker else None

    # Validate action against registry
    if action not in WEBHOOK_ACTION_REGISTRY:
        supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
        return {"success": False, "message": f"不支援的 action: {action}。支援：{supported}"}

    if action == "help":
        return {
            "success": True,
            "message": "以下是所有支援的 webhook actions。",
            "data": {"actions": WEBHOOK_ACTION_REGISTRY},
        }

    if action == "summary":
        text = get_portfolio_summary(session)
        return {"success": True, "message": text}

    if action == "signals":
        if not ticker:
            return {"success": False, "message": WEBHOOK_MISSING_TICKER}
        result = get_technical_signals(ticker)
        if not result or "error" in result:
            return {
                "success": False,
                "message": result.get("error", "無法取得技術訊號。") if result else "無法取得技術訊號。",
            }
        status_text = "\n".join(result.get("status", []))
        msg = (
            f"{ticker} — 現價 ${result.get('price')}, RSI={result.get('rsi')}, "
            f"Bias={result.get('bias')}%\n{status_text}"
        )
        return {"success": True, "message": msg, "data": result}

    if action == "scan":
        from infrastructure.database import engine as _engine

        def _bg_scan() -> None:
            with Session(_engine) as s:
                run_scan(s)

        _threading.Thread(target=_bg_scan, daemon=True).start()
        return {"success": True, "message": "掃描已在背景啟動，結果將透過 Telegram 通知。"}

    if action == "moat":
        if not ticker:
            return {"success": False, "message": WEBHOOK_MISSING_TICKER}
        result = analyze_moat_trend(ticker)
        details = result.get("details", "N/A")
        return {
            "success": True,
            "message": f"{ticker} 護城河：{result.get('moat', 'N/A')} — {details}",
            "data": result,
        }

    if action == "alerts":
        if not ticker:
            return {"success": False, "message": WEBHOOK_MISSING_TICKER}
        alerts = list_price_alerts(session, ticker)
        if not alerts:
            return {"success": True, "message": f"{ticker} 目前沒有設定價格警報。"}
        lines = [f"{ticker} 價格警報："]
        for a in alerts:
            op_str = "<" if a["operator"] == "lt" else ">"
            lines.append(f"  {a['metric']} {op_str} {a['threshold']} ({'啟用' if a['is_active'] else '停用'})")
        return {"success": True, "message": "\n".join(lines), "data": {"alerts": alerts}}

    if action == "fear_greed":
        fg = get_fear_greed_index()
        fg_label = format_fear_greed_label(
            fg.get("composite_level", "N/A"),
            fg.get("composite_score", 50),
        )
        vix_data = fg.get("vix", {})
        vix_val = vix_data.get("value")
        vix_text = f"VIX={vix_val}" if vix_val is not None else "VIX=N/A"
        cnn_data = fg.get("cnn")
        cnn_text = f"CNN={cnn_data['score']}" if cnn_data and cnn_data.get("score") is not None else "CNN=N/A"
        msg = f"恐懼貪婪指數：{fg_label}\n{vix_text}, {cnn_text}"
        return {"success": True, "message": msg, "data": fg}

    if action == "add_stock":
        t = params.get("ticker", ticker)
        if not t:
            return {"success": False, "message": WEBHOOK_MISSING_TICKER}
        cat_str = params.get("category", DEFAULT_IMPORT_CATEGORY)
        thesis = params.get("thesis", DEFAULT_WEBHOOK_THESIS)
        tags = params.get("tags", [])
        try:
            stock = create_stock(session, t, StockCategory(cat_str), thesis, tags)
            return {"success": True, "message": f"✅ 已新增 {stock.ticker} 到 {cat_str} 分類。"}
        except StockAlreadyExistsError as e:
            return {"success": False, "message": str(e)}
        except ValueError:
            return {"success": False, "message": f"無效的分類：{cat_str}"}

    # Fallback — should not reach here if registry is in sync
    supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
    return {"success": False, "message": f"不支援的 action: {action}。支援：{supported}"}
