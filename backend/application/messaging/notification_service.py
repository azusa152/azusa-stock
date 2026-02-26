"""
Application — Notification Service：每週摘要、投資組合摘要。
"""

import json
import os
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from application.formatters import (
    format_fear_greed_label,
    format_fear_greed_short,
    format_guru_filing_digest,
    format_resonance_alert,
    format_weekly_digest_html,
)
from domain.analysis import compute_signal_duration
from domain.constants import (
    CATEGORY_DISPLAY_ORDER,
    DATA_DIR,
    DRIFT_THRESHOLD_PCT,
    NOTIFICATION_TYPE_GURU_ALERTS,
    WEEKLY_DIGEST_LOOKBACK_DAYS,
)
from domain.enums import CATEGORY_LABEL, HoldingAction, ScanSignal
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.market_data import get_fear_greed_index, get_technical_signals
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from logging_config import get_logger

logger = get_logger(__name__)

# Actions that warrant a resonance alert notification
_ALERT_ACTIONS: frozenset[str] = frozenset(
    {HoldingAction.NEW_POSITION.value, HoldingAction.SOLD_OUT.value}
)

# ---------------------------------------------------------------------------
# WoW (week-over-week) state persistence helpers
# ---------------------------------------------------------------------------

_WOW_STATE_FILE = os.path.join(DATA_DIR, "weekly_digest_state.json")


def _load_wow_state() -> dict:
    """Load persisted digest state (previous total portfolio value)."""
    try:
        with open(_WOW_STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_wow_state(state: dict) -> None:
    """Persist digest state, ignoring write errors (e.g. read-only FS in tests)."""
    try:
        os.makedirs(os.path.dirname(_WOW_STATE_FILE), exist_ok=True)
        with open(_WOW_STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError as exc:
        logger.warning("無法儲存每週摘要狀態：%s", exc)


# ===========================================================================
# Weekly Digest Service
# ===========================================================================


def send_weekly_digest(session: Session) -> dict:
    """
    發送每週 Telegram 摘要：
    - 投資組合總值 + 週漲跌幅（WoW）
    - S&P 500 基準 + Alpha
    - 投資組合健康分數
    - 恐懼貪婪指數
    - 本週漲跌幅前三名
    - 目前所有非 NORMAL 股票
    - 過去 7 天訊號變化
    - 配置偏移
    - Smart Money 大師動態
    """
    logger.info("開始生成每週摘要...")
    lang = get_user_language(session)

    all_stocks = repo.find_active_stocks(session)
    total = len(all_stocks)
    if total == 0:
        message = (
            t("notification.weekly_digest_title", lang=lang)
            + "\n"
            + t("notification.no_stocks", lang=lang)
        )
        send_telegram_message_dual(message, session)
        return {"message": t("notification.no_stocks", lang=lang)}

    # --- 目前非 NORMAL 股票 ---
    non_normal_stocks = [
        s for s in all_stocks if s.last_scan_signal != ScanSignal.NORMAL.value
    ]
    normal_count = total - len(non_normal_stocks)
    health_score = round(normal_count / total * 100, 1)

    # --- 過去 7 天的訊號變化（含轉換方向）---
    now_ts = datetime.now(UTC)
    seven_days_ago = now_ts - timedelta(days=WEEKLY_DIGEST_LOOKBACK_DAYS)
    recent_logs = repo.find_scan_logs_since(session, seven_days_ago)
    signal_changes: dict[str, int] = {}
    signal_transitions: dict[str, tuple[str, str]] = {}  # ticker → (earliest, latest)
    prev_signals: dict[str, str] = {}
    for log in reversed(recent_logs):
        tk = log.stock_ticker
        if tk in prev_signals and prev_signals[tk] != log.signal:
            signal_changes[tk] = signal_changes.get(tk, 0) + 1
            if tk not in signal_transitions:
                signal_transitions[tk] = (prev_signals[tk], log.signal)
            else:
                signal_transitions[tk] = (signal_transitions[tk][0], log.signal)
        prev_signals[tk] = log.signal

    # --- 恐懼貪婪指數 ---
    fg = get_fear_greed_index()
    fg_label = format_fear_greed_label(
        fg.get("composite_level", "N/A"), fg.get("composite_score", 50), lang=lang
    )
    vix_val = fg.get("vix", {}).get("value")
    vix_text = f"VIX={vix_val}" if vix_val is not None else "VIX=N/A"

    # --- 投資組合總值 + WoW ---
    # Lazy import to avoid circular dependency: notification_service ↔ rebalance_service.
    portfolio_value_line: str | None = None
    current_total: float | None = None
    prev_total: float | None = None
    display_currency = "USD"
    holdings_detail: list[dict] = []
    categories: dict = {}
    try:
        from application.portfolio.rebalance_service import calculate_rebalance

        rebalance = calculate_rebalance(session)
        current_total = rebalance.get("total_value")
        display_currency = rebalance.get("display_currency", "USD")
        holdings_detail = rebalance.get("holdings_detail", [])
        categories = rebalance.get("categories", {})
    except Exception as exc:
        logger.warning("無法取得再平衡資料：%s", exc)

    if current_total is not None:
        wow_state = _load_wow_state()
        prev_total = wow_state.get("last_total_value")
        if prev_total and prev_total > 0:
            wow_abs = current_total - prev_total
            wow_pct = wow_abs / prev_total * 100
            sign = "+" if wow_pct >= 0 else ""
            sign_abs = "+" if wow_abs >= 0 else "-"
            portfolio_value_line = t(
                "notification.portfolio_value",
                lang=lang,
                currency=display_currency,
                value=f"{current_total:,.0f}",
                sign=sign,
                pct=f"{abs(wow_pct):.1f}",
                sign_abs=sign_abs,
                abs_change=f"{abs(wow_abs):,.0f}",
            )
        else:
            portfolio_value_line = f"💰 {display_currency} {current_total:,.0f}"
        # Always persist the current total so next week's digest can compute WoW.
        # This runs regardless of is_notification_enabled so that a single disabled
        # week doesn't cause an artificially large WoW delta the following week.
        wow_state["last_total_value"] = current_total
        _save_wow_state(wow_state)

    # --- S&P 500 基準 + Alpha ---
    # NOTE: get_technical_signals returns a *daily* change_pct (previous close vs
    # current), not a weekly one.  Alpha here is therefore portfolio-WoW vs S&P-daily,
    # which is an approximation only meaningful when the digest runs weekly — callers
    # should treat it as indicative, not precise.
    # `prev_total` captured above is the value from the *previous* run, before saving.
    benchmark_line: str | None = None
    try:
        sp500 = get_technical_signals("^GSPC")
        sp500_pct = sp500.get("change_pct")
        if sp500_pct is not None and current_total is not None:
            if prev_total and prev_total > 0:
                port_pct = (current_total - prev_total) / prev_total * 100
                alpha: float | None = port_pct - sp500_pct
            else:
                alpha = None
            sp_sign = "+" if sp500_pct >= 0 else ""
            if alpha is not None:
                alpha_sign = "+" if alpha >= 0 else "-"
                alpha_str = f"{abs(alpha):.1f}"
            else:
                alpha_sign = ""
                alpha_str = "N/A"
            benchmark_line = t(
                "notification.benchmark_label",
                lang=lang,
                sign=sp_sign,
                pct=f"{abs(sp500_pct):.1f}",
                sign_a=alpha_sign,
                alpha=alpha_str,
            )
    except Exception as exc:
        logger.warning("無法取得 S&P 500 資料：%s", exc)

    # --- 本週漲跌幅前三名 ---
    top_movers_lines: list[str] = []
    if holdings_detail:
        valid = [h for h in holdings_detail if h.get("change_pct") is not None]
        gainers = sorted(valid, key=lambda h: h["change_pct"], reverse=True)[:3]
        losers = sorted(valid, key=lambda h: h["change_pct"])[:3]
        gainer_parts = [
            f"  ▲ {h['ticker']} {h['change_pct']:+.1f}%"
            for h in gainers
            if h["change_pct"] > 0
        ]
        loser_parts = [
            f"  ▼ {h['ticker']} {h['change_pct']:+.1f}%"
            for h in losers
            if h["change_pct"] < 0
        ]
        if gainer_parts:
            top_movers_lines.append("  ".join(gainer_parts))
        if loser_parts:
            top_movers_lines.append("  ".join(loser_parts))

    # --- 配置偏移 ---
    drift_lines: list[str] = []
    for cat, data in categories.items():
        drift = data.get("drift_pct", 0.0)
        if abs(drift) >= DRIFT_THRESHOLD_PCT:
            cat_label = CATEGORY_LABEL.get(cat, cat)
            key = (
                "notification.drift_item_over"
                if drift > 0
                else "notification.drift_item_under"
            )
            drift_lines.append(
                t(key, lang=lang, cat=cat_label, pct=f"{abs(drift):.1f}")
            )

    # --- Smart Money 大師動態 ---
    # Lazy import to avoid circular dependency: notification_service ↔ resonance_service.
    smart_money_lines: list[str] = []
    try:
        from application.guru.resonance_service import compute_portfolio_resonance

        resonance = compute_portfolio_resonance(session)
        for entry in resonance:
            guru_name = entry["guru_display_name"]
            for holding in entry["holdings"]:
                if holding["action"] in _ALERT_ACTIONS:
                    smart_money_lines.append(
                        format_resonance_alert(
                            holding["ticker"], guru_name, holding["action"], lang=lang
                        )
                    )
    except Exception as exc:
        logger.warning("無法取得 Smart Money 資料：%s", exc)

    # --- 組合訊息 ---
    non_normal_dicts: list[dict] = []
    for s in non_normal_stocks:
        duration_days, is_new = compute_signal_duration(s.signal_since, now_ts)
        non_normal_dicts.append(
            {
                "ticker": s.ticker,
                "cat_label": CATEGORY_LABEL.get(s.category.value, s.category.value),
                "signal": s.last_scan_signal,
                "duration_days": duration_days,
                "is_new": is_new,
            }
        )
    message = format_weekly_digest_html(
        lang=lang,
        title=t("notification.weekly_digest_title", lang=lang),
        portfolio_value_line=portfolio_value_line,
        benchmark_line=benchmark_line,
        health_line=t(
            "notification.health_score",
            lang=lang,
            score=health_score,
            normal=normal_count,
            total=total,
        ),
        fear_greed_line=t(
            "notification.fear_greed", lang=lang, label=fg_label, vix=vix_text
        ),
        top_movers_lines=top_movers_lines,
        non_normal=non_normal_dicts,
        signal_changes=signal_changes,
        signal_transitions=signal_transitions,
        drift_lines=drift_lines,
        smart_money_lines=smart_money_lines,
        all_normal_line=t("notification.all_normal", lang=lang),
    )

    if is_notification_enabled(session, "weekly_digest"):
        send_telegram_message_dual(message, session)
        logger.info("每週摘要已發送。")
    else:
        logger.info("每週摘要通知已被使用者停用，跳過發送。")

    return {
        "message": t("notification.summary_sent", lang=lang),
        "health_score": health_score,
    }


# ===========================================================================
# Portfolio Summary Service (for OpenClaw / chat)
# ===========================================================================


def get_portfolio_summary(session: Session) -> str:
    """
    產生純文字投資組合摘要，專為 chat / AI agent 設計。

    包含：
    - 健康分數 + 恐懼貪婪指數
    - 投資組合總值 + 日漲跌幅
    - 類別持倉清單
    - 目前非 NORMAL 股票
    - 漲跌幅前三名
    - 配置偏移警告
    - Smart Money 大師動態
    """
    lang = get_user_language(session)
    stocks = repo.find_active_stocks(session)
    if not stocks:
        return t("notification.portfolio_summary_no_stocks", lang=lang)

    non_normal = [s for s in stocks if s.last_scan_signal != ScanSignal.NORMAL.value]
    health = round((len(stocks) - len(non_normal)) / len(stocks) * 100, 1)

    # 恐懼貪婪指數
    fg = get_fear_greed_index()
    fg_short = format_fear_greed_short(fg.get("composite_level", "N/A"), lang=lang)

    lines: list[str] = [
        t(
            "notification.portfolio_summary_health",
            lang=lang,
            health=health,
            fg=fg_short,
        ),
        "",
    ]

    # --- 投資組合總值 + 日漲跌幅 ---
    holdings_detail: list[dict] = []
    categories: dict = {}
    display_currency = "USD"
    try:
        from application.portfolio.rebalance_service import calculate_rebalance

        rebalance = calculate_rebalance(session)
        current_total = rebalance.get("total_value")
        display_currency = rebalance.get("display_currency", "USD")
        holdings_detail = rebalance.get("holdings_detail", [])
        categories = rebalance.get("categories", {})
        if current_total is not None:
            daily_pct = rebalance.get("total_value_change_pct")
            if daily_pct is not None:
                sign = "+" if daily_pct >= 0 else "-"
                lines.append(
                    t(
                        "notification.portfolio_summary_value",
                        lang=lang,
                        currency=display_currency,
                        value=f"{current_total:,.0f}",
                        sign=sign,
                        pct=f"{abs(daily_pct):.1f}",
                    )
                )
            else:
                lines.append(f"💰 {display_currency} {current_total:,.0f}")
            lines.append("")
    except Exception as exc:
        logger.warning("portfolio_summary: 無法取得再平衡資料：%s", exc)

    # --- 類別持倉清單 ---
    for cat in CATEGORY_DISPLAY_ORDER:
        group = [s for s in stocks if s.category.value == cat]
        if group:
            label = CATEGORY_LABEL.get(cat, cat)
            lines.append(f"[{label}] {', '.join(s.ticker for s in group)}")

    # --- 目前非 NORMAL 股票 ---
    if non_normal:
        lines += ["", t("notification.portfolio_summary_abnormal", lang=lang)]
        for s in non_normal:
            lines.append(f"  {s.ticker} -> {s.last_scan_signal}")
    else:
        lines += ["", t("notification.portfolio_summary_normal", lang=lang)]

    # --- 漲跌幅前三名 ---
    if holdings_detail:
        valid = [h for h in holdings_detail if h.get("change_pct") is not None]
        gainers = sorted(valid, key=lambda h: h["change_pct"], reverse=True)[:3]
        losers = sorted(valid, key=lambda h: h["change_pct"])[:3]
        gainer_parts = [
            f"▲ {h['ticker']} {h['change_pct']:+.1f}%"
            for h in gainers
            if h["change_pct"] > 0
        ]
        loser_parts = [
            f"▼ {h['ticker']} {h['change_pct']:+.1f}%"
            for h in losers
            if h["change_pct"] < 0
        ]
        if gainer_parts or loser_parts:
            lines += ["", t("notification.top_movers_title", lang=lang)]
            if gainer_parts:
                lines.append("  " + "  ".join(gainer_parts))
            if loser_parts:
                lines.append("  " + "  ".join(loser_parts))

    # --- 配置偏移警告 ---
    drift_lines: list[str] = []
    for cat, data in categories.items():
        drift = data.get("drift_pct", 0.0)
        if abs(drift) >= DRIFT_THRESHOLD_PCT:
            cat_label = CATEGORY_LABEL.get(cat, cat)
            key = (
                "notification.drift_item_over"
                if drift > 0
                else "notification.drift_item_under"
            )
            drift_lines.append(
                t(key, lang=lang, cat=cat_label, pct=f"{abs(drift):.1f}")
            )
    if drift_lines:
        lines += ["", t("notification.drift_title", lang=lang)]
        lines.extend(drift_lines)

    # --- Smart Money 大師動態 ---
    try:
        from application.guru.resonance_service import compute_portfolio_resonance

        resonance = compute_portfolio_resonance(session)
        smart_lines: list[str] = []
        for entry in resonance:
            guru_name = entry["guru_display_name"]
            for holding in entry["holdings"]:
                if holding["action"] in _ALERT_ACTIONS:
                    smart_lines.append(
                        format_resonance_alert(
                            holding["ticker"], guru_name, holding["action"], lang=lang
                        )
                    )
        if smart_lines:
            lines += ["", t("notification.smart_money_title", lang=lang)]
            lines.extend(smart_lines)
    except Exception as exc:
        logger.warning("portfolio_summary: 無法取得 Smart Money 資料：%s", exc)

    return "\n".join(lines)


# ===========================================================================
# Smart Money — Guru 通知服務
# ===========================================================================


def send_filing_season_digest(session: Session) -> dict:
    """
    發送本季所有大師的 13F 季報摘要 Telegram 通知。

    功能：
    - 取得所有啟用中大師的最新申報摘要
    - 格式化為多大師彙整訊息
    - 依 guru_alerts 通知偏好決定是否發送

    Args:
        session: Database session

    Returns:
        dict with keys: status ("sent" | "skipped" | "no_data"),
                        message (str), guru_count (int)
    """
    from application.stock.filing_service import get_filing_summary

    lang = get_user_language(session)

    if not is_notification_enabled(session, NOTIFICATION_TYPE_GURU_ALERTS):
        logger.info("guru_alerts 通知已停用，跳過季報摘要發送。")
        return {"status": "skipped", "message": "guru_alerts disabled", "guru_count": 0}

    gurus = repo.find_all_active_gurus(session)
    summaries = []
    for guru in gurus:
        summary = get_filing_summary(session, guru.id)
        if summary is not None:
            summaries.append(summary)

    if not summaries:
        logger.info("無可用的大師申報資料，跳過季報摘要發送。")
        return {"status": "no_data", "message": "no filings available", "guru_count": 0}

    message = format_guru_filing_digest(summaries, lang=lang)
    send_telegram_message_dual(message, session)
    logger.info("13F 季報摘要已發送，共 %d 位大師。", len(summaries))
    return {
        "status": "sent",
        "message": t("guru.digest_sent", lang=lang, count=len(summaries)),
        "guru_count": len(summaries),
    }


def send_resonance_alerts(session: Session) -> dict:
    """
    當大師最新動作（NEW_POSITION / SOLD_OUT）與使用者關注清單重疊時，
    發送一則彙整的共鳴警報通知。

    功能：
    - 計算所有大師與使用者投資組合的共鳴結果
    - 篩選出有顯著動作（新建倉或清倉）的重疊股票
    - 將所有警報行彙整為單一 Telegram 訊息（含標題）後一次送出

    Args:
        session: Database session

    Returns:
        dict with keys: status, alert_count, alerts (list of dicts)
    """
    from application.guru.resonance_service import compute_portfolio_resonance

    lang = get_user_language(session)

    if not is_notification_enabled(session, NOTIFICATION_TYPE_GURU_ALERTS):
        logger.info("guru_alerts 通知已停用，跳過共鳴警報發送。")
        return {"status": "skipped", "alert_count": 0, "alerts": []}

    resonance = compute_portfolio_resonance(session)

    alert_lines: list[str] = []
    sent_alerts: list[dict] = []

    for entry in resonance:
        guru_name = entry["guru_display_name"]
        for holding in entry["holdings"]:
            if holding["action"] not in _ALERT_ACTIONS:
                continue
            ticker = holding["ticker"]
            action = holding["action"]
            alert_lines.append(
                format_resonance_alert(ticker, guru_name, action, lang=lang)
            )
            sent_alerts.append(
                {"ticker": ticker, "guru_name": guru_name, "action": action}
            )

    if alert_lines:
        parts = [t("guru.resonance_alerts_title", lang=lang), ""] + alert_lines
        parts.append(t("guru.lagging_disclaimer_short", lang=lang))
        send_telegram_message_dual("\n".join(parts), session)

    logger.info("共鳴警報發送完成，共 %d 則。", len(sent_alerts))
    return {
        "status": "sent",
        "alert_count": len(sent_alerts),
        "alerts": sent_alerts,
    }
