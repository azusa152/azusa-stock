"""
Application — Webhook Service：OpenClaw / AI agent webhook 處理。
"""

from sqlmodel import Session

from application.filing_service import sync_all_gurus
from application.formatters import format_fear_greed_label
from application.fx_watch_service import send_fx_watch_alerts
from application.notification_service import (
    get_portfolio_summary,
    send_filing_season_digest,
)
from application.stock_service import (
    StockAlreadyExistsError,
    StockNotFoundError,
    create_stock,
)
from application.scan_service import list_price_alerts, run_scan
from application.rebalance_service import calculate_withdrawal
from domain.constants import (
    DEFAULT_IMPORT_CATEGORY,
    DEFAULT_WEBHOOK_THESIS,
    WEBHOOK_ACTION_REGISTRY,
)
from domain.enums import StockCategory
from i18n import get_user_language, t
from infrastructure.market_data import (
    analyze_moat_trend,
    get_fear_greed_index,
    get_technical_signals,
)
from logging_config import get_logger

logger = get_logger(__name__)


def handle_webhook(
    session: Session, action: str, ticker: str | None, params: dict
) -> dict:
    """
    處理 AI agent webhook 請求。回傳 dict(success, message, data)。
    業務邏輯集中於此，API handler 只負責 parse + 回傳。
    """
    import threading as _threading

    lang = get_user_language(session)
    action = action.lower().strip()
    ticker = ticker.upper().strip() if ticker else None

    # Validate action against registry
    if action not in WEBHOOK_ACTION_REGISTRY:
        supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
        return {
            "success": False,
            "message": t(
                "webhook.unsupported_action",
                lang=lang,
                action=action,
                supported=supported,
            ),
        }

    if action == "help":
        return {
            "success": True,
            "message": t("webhook.help_message", lang=lang),
            "data": {"actions": WEBHOOK_ACTION_REGISTRY},
        }

    if action == "summary":
        text = get_portfolio_summary(session)
        return {"success": True, "message": text}

    if action == "signals":
        if not ticker:
            return {"success": False, "message": t("webhook.missing_ticker", lang=lang)}
        result = get_technical_signals(ticker)
        if not result or "error" in result:
            return {
                "success": False,
                "message": result.get(
                    "error", t("webhook.signals_unavailable", lang=lang)
                )
                if result
                else t("webhook.signals_unavailable", lang=lang),
            }
        status_text = "\n".join(result.get("status", []))
        msg = (
            t(
                "webhook.signals_line",
                lang=lang,
                ticker=ticker,
                price=result.get("price"),
                rsi=result.get("rsi"),
                bias=result.get("bias"),
            )
            + f"\n{status_text}"
        )
        return {"success": True, "message": msg, "data": result}

    if action == "scan":
        from infrastructure.database import engine as _engine

        def _bg_scan() -> None:
            with Session(_engine) as s:
                run_scan(s)

        _threading.Thread(target=_bg_scan, daemon=True).start()
        return {
            "success": True,
            "message": t("webhook.scan_started", lang=lang),
        }

    if action == "moat":
        if not ticker:
            return {"success": False, "message": t("webhook.missing_ticker", lang=lang)}
        result = analyze_moat_trend(ticker)
        details = result.get("details", "N/A")
        return {
            "success": True,
            "message": t(
                "webhook.moat_result",
                lang=lang,
                ticker=ticker,
                moat=result.get("moat", "N/A"),
                details=details,
            ),
            "data": result,
        }

    if action == "alerts":
        if not ticker:
            return {"success": False, "message": t("webhook.missing_ticker", lang=lang)}
        alerts = list_price_alerts(session, ticker)
        if not alerts:
            return {
                "success": True,
                "message": t("webhook.no_alerts", lang=lang, ticker=ticker),
            }
        lines = [t("webhook.price_alerts_header", lang=lang, ticker=ticker)]
        for a in alerts:
            op_str = "<" if a["operator"] == "lt" else ">"
            status_label = t("webhook.alert_status.active", lang=lang)
            inactive_label = t("webhook.alert_status.inactive", lang=lang)
            lines.append(
                f"  {a['metric']} {op_str} {a['threshold']} ({status_label if a['is_active'] else inactive_label})"
            )
        return {
            "success": True,
            "message": "\n".join(lines),
            "data": {"alerts": alerts},
        }

    if action == "fear_greed":
        fg = get_fear_greed_index()
        fg_label = format_fear_greed_label(
            fg.get("composite_level", "N/A"),
            fg.get("composite_score", 50),
            lang=lang,
        )
        vix_data = fg.get("vix", {})
        vix_val = vix_data.get("value")
        vix_text = f"VIX={vix_val}" if vix_val is not None else "VIX=N/A"
        cnn_data = fg.get("cnn")
        cnn_text = (
            f"CNN={cnn_data['score']}"
            if cnn_data and cnn_data.get("score") is not None
            else "CNN=N/A"
        )
        fg_label_prefix = t("webhook.fear_greed_prefix", lang=lang)
        msg = f"{fg_label_prefix}：{fg_label}\n{vix_text}, {cnn_text}"
        return {"success": True, "message": msg, "data": fg}

    if action == "add_stock":
        t_ticker = params.get("ticker", ticker)
        if not t_ticker:
            return {"success": False, "message": t("webhook.missing_ticker", lang=lang)}
        cat_str = params.get("category", DEFAULT_IMPORT_CATEGORY)
        thesis = params.get("thesis") or t(DEFAULT_WEBHOOK_THESIS, lang=lang)
        tags = params.get("tags", [])
        try:
            stock = create_stock(
                session, t_ticker, StockCategory(cat_str), thesis, tags
            )
            return {
                "success": True,
                "message": t(
                    "stock.added", lang=lang, ticker=stock.ticker, category=cat_str
                ),
            }
        except StockAlreadyExistsError as e:
            return {"success": False, "message": str(e)}
        except ValueError:
            return {
                "success": False,
                "message": t("webhook.invalid_category", lang=lang, category=cat_str),
            }

    if action == "withdraw":
        amount = params.get("amount")
        if not amount:
            return {"success": False, "message": t("webhook.missing_amount", lang=lang)}
        try:
            amount_float = float(amount)
        except (ValueError, TypeError):
            return {
                "success": False,
                "message": t("webhook.invalid_amount", lang=lang, amount=amount),
            }
        currency = params.get("currency", "USD")
        try:
            result = calculate_withdrawal(session, amount_float, currency, notify=True)
            return {
                "success": True,
                "message": result.get("message", ""),
                "data": result,
            }
        except StockNotFoundError as e:
            return {"success": False, "message": str(e)}

    if action == "fx_watch":
        try:
            result = send_fx_watch_alerts(session)
            msg = t(
                "webhook.fx_watch_complete",
                lang=lang,
                total=result["total_watches"],
                triggered=result["triggered_alerts"],
                sent=result["sent_alerts"],
            )
            return {
                "success": True,
                "message": msg,
                "data": result,
            }
        except Exception as e:
            logger.error("外匯監控執行失敗：%s", e)
            return {
                "success": False,
                "message": t("webhook.fx_watch_failed", lang=lang, error=str(e)),
            }

    if action == "guru_sync":
        try:
            results = sync_all_gurus(session)
            synced = sum(1 for r in results if r.get("status") == "synced")
            skipped = sum(1 for r in results if r.get("status") == "skipped")
            errors = sum(1 for r in results if r.get("status") == "error")
            msg = t(
                "webhook.guru_sync_complete",
                lang=lang,
                total=len(results),
                synced=synced,
                skipped=skipped,
                errors=errors,
            )
            return {
                "success": True,
                "message": msg,
                "data": {
                    "total": len(results),
                    "synced": synced,
                    "skipped": skipped,
                    "errors": errors,
                },
            }
        except Exception as e:
            logger.error("guru_sync 執行失敗：%s", e)
            return {
                "success": False,
                "message": t("webhook.guru_sync_failed", lang=lang, error=str(e)),
            }

    if action == "guru_summary":
        try:
            result = send_filing_season_digest(session)
            msg = t(
                "webhook.guru_summary_complete",
                lang=lang,
                status=result.get("status", ""),
                count=result.get("guru_count", 0),
            )
            return {
                "success": True,
                "message": msg,
                "data": result,
            }
        except Exception as e:
            logger.error("guru_summary 執行失敗：%s", e)
            return {
                "success": False,
                "message": t("webhook.guru_summary_failed", lang=lang, error=str(e)),
            }

    # Fallback — should not reach here if registry is in sync
    supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
    return {
        "success": False,
        "message": t(
            "webhook.unsupported_action", lang=lang, action=action, supported=supported
        ),
    }
