"""
Application — Notification Service：每週摘要、投資組合摘要。
"""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from application.formatters import format_fear_greed_label, format_fear_greed_short
from domain.constants import (
    CATEGORY_DISPLAY_ORDER,
    WEEKLY_DIGEST_LOOKBACK_DAYS,
)
from domain.enums import CATEGORY_LABEL, ScanSignal
from infrastructure import repositories as repo
from infrastructure.market_data import get_fear_greed_index
from infrastructure.notification import is_notification_enabled, send_telegram_message_dual
from logging_config import get_logger

logger = get_logger(__name__)


# ===========================================================================
# Weekly Digest Service
# ===========================================================================


def send_weekly_digest(session: Session) -> dict:
    """
    發送每週 Telegram 摘要：
    - 目前所有非 NORMAL 股票
    - 過去 7 天訊號變化
    - 投資組合健康分數
    """
    logger.info("開始生成每週摘要...")

    all_stocks = repo.find_active_stocks(session)
    total = len(all_stocks)
    if total == 0:
        send_telegram_message_dual("📊 <b>Folio 每週摘要</b>\n\n目前無追蹤股票。", session)
        return {"message": "無追蹤股票。"}

    # 目前非 NORMAL 股票
    non_normal = [s for s in all_stocks if s.last_scan_signal != ScanSignal.NORMAL.value]
    normal_count = total - len(non_normal)
    health_score = round(normal_count / total * 100, 1)

    # 過去 7 天的訊號變化
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=WEEKLY_DIGEST_LOOKBACK_DAYS)
    recent_logs = repo.find_scan_logs_since(session, seven_days_ago)

    # 統計每檔股票的訊號變化次數
    signal_changes: dict[str, int] = {}
    prev_signals: dict[str, str] = {}
    # 按時間正序處理（最舊→最新）
    for log in reversed(recent_logs):
        tk = log.stock_ticker
        if tk in prev_signals and prev_signals[tk] != log.signal:
            signal_changes[tk] = signal_changes.get(tk, 0) + 1
        prev_signals[tk] = log.signal

    # 恐懼貪婪指數
    fg = get_fear_greed_index()
    fg_label = format_fear_greed_label(fg.get("composite_level", "N/A"), fg.get("composite_score", 50))
    vix_val = fg.get("vix", {}).get("value")
    vix_text = f"VIX={vix_val}" if vix_val is not None else "VIX=N/A"

    # 組合訊息
    parts: list[str] = [
        f"📊 <b>Folio 每週摘要</b>\n",
        f"🏥 投資組合健康分數：<b>{health_score}%</b>（{normal_count}/{total} 正常）",
        f"📈 恐懼貪婪指數：{fg_label}（{vix_text}）\n",
    ]

    if non_normal:
        parts.append("⚠️ <b>目前異常股票：</b>")
        for s in non_normal:
            cat_label = CATEGORY_LABEL.get(s.category.value, s.category.value)
            parts.append(f"  • {s.ticker}（{cat_label}）→ {s.last_scan_signal}")

    if signal_changes:
        parts.append("\n🔄 <b>本週訊號變化：</b>")
        for tk, count in sorted(signal_changes.items(), key=lambda x: -x[1]):
            parts.append(f"  • {tk}：變化 {count} 次")

    if not non_normal and not signal_changes:
        parts.append("✅ 一切正常，本週無異常訊號。")

    message = "\n".join(parts)
    if is_notification_enabled(session, "weekly_digest"):
        send_telegram_message_dual(message, session)
        logger.info("每週摘要已發送。")
    else:
        logger.info("每週摘要通知已被使用者停用，跳過發送。")

    return {"message": "每週摘要已發送。", "health_score": health_score}


# ===========================================================================
# Portfolio Summary Service (for OpenClaw / chat)
# ===========================================================================


def get_portfolio_summary(session: Session) -> str:
    """
    產生純文字投資組合摘要，專為 chat / AI agent 設計。
    """
    stocks = repo.find_active_stocks(session)
    if not stocks:
        return "Folio — 目前無追蹤股票。"

    non_normal = [s for s in stocks if s.last_scan_signal != ScanSignal.NORMAL.value]
    health = round((len(stocks) - len(non_normal)) / len(stocks) * 100, 1)

    # 恐懼貪婪指數
    fg = get_fear_greed_index()
    fg_short = format_fear_greed_short(fg.get("composite_level", "N/A"))

    lines: list[str] = [f"Folio — Health: {health}% | F&G: {fg_short}", ""]

    for cat in CATEGORY_DISPLAY_ORDER:
        group = [s for s in stocks if s.category.value == cat]
        if group:
            label = CATEGORY_LABEL.get(cat, cat)
            lines.append(f"[{label}] {', '.join(s.ticker for s in group)}")

    if non_normal:
        lines += ["", "Abnormal:"]
        for s in non_normal:
            lines.append(f"  {s.ticker} -> {s.last_scan_signal}")
    else:
        lines += ["", "All signals normal."]

    return "\n".join(lines)
