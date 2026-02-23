"""
Application — Scan Service：三層漏斗掃描、價格警報、掃描歷史。
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from application.formatters import format_fear_greed_label
from application.stock_service import _get_stock_or_raise
from domain.analysis import (
    compute_bias_percentile,
    detect_rogue_wave,
    determine_scan_signal,
)
from domain.constants import (
    CATEGORY_DISPLAY_ORDER,
    CATEGORY_ICON,
    DEFAULT_IMPORT_CATEGORY,
    LATEST_SCAN_LOGS_DEFAULT_LIMIT,
    PRICE_ALERT_COOLDOWN_HOURS,
    SCAN_HISTORY_DEFAULT_LIMIT,
    SCAN_THREAD_POOL_SIZE,
    SKIP_MOAT_CATEGORIES,
    SKIP_SIGNALS_CATEGORIES,
    VOLUME_SURGE_THRESHOLD,
    VOLUME_THIN_THRESHOLD,
)
from domain.entities import PriceAlert, ScanLog, Stock
from domain.enums import (
    CATEGORY_LABEL,
    MarketSentiment,
    MoatStatus,
    ScanSignal,
    StockCategory,
)
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.market_data import (
    analyze_market_sentiment,
    analyze_moat_trend,
    get_bias_distribution,
    get_fear_greed_index,
    get_technical_signals,
)
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from logging_config import get_logger

logger = get_logger(__name__)


# ===========================================================================
# Scan Service
# ===========================================================================


def run_scan(session: Session) -> dict:
    """
    V2 三層漏斗掃描：
    Layer 1: 市場情緒（風向球跌破 60MA 比例）
    Layer 2: 護城河趨勢（毛利率 YoY）
    Layer 3: 技術面訊號（RSI, Bias, Volume Ratio）
    Decision Engine 產生每檔股票的 signal，並透過 Telegram 通知。
    """
    logger.info("三層漏斗掃描啟動...")
    lang = get_user_language(session)

    # === Layer 1: 市場情緒 ===
    trend_stocks = repo.find_active_stocks_by_category(
        session, StockCategory.TREND_SETTER
    )
    # ETF 不參與市場情緒計算（VTI/VT 本身就是大盤，會造成循環推理）
    excluded_etfs = [s.ticker for s in trend_stocks if s.is_etf]
    if excluded_etfs:
        logger.info("Layer 1 — 排除 ETF：%s", excluded_etfs)
    trend_tickers = [s.ticker for s in trend_stocks if not s.is_etf]
    logger.info("Layer 1 — 風向球股票（情緒計算用）：%s", trend_tickers)

    market_sentiment = analyze_market_sentiment(trend_tickers)
    market_status_value = market_sentiment.get("status", MarketSentiment.POSITIVE.value)
    market_status_details_value = market_sentiment.get("details", "")
    logger.info(
        "Layer 1 — 市場情緒：%s（%s）", market_status_value, market_status_details_value
    )

    # === Fear & Greed Index（與 Layer 1 並列的市場概況） ===
    fear_greed = get_fear_greed_index()
    fg_level = fear_greed.get("composite_level", "N/A")
    fg_score = fear_greed.get("composite_score", 50)
    fg_label = format_fear_greed_label(fg_level, fg_score, lang=lang)
    logger.info("恐懼貪婪指數：%s（分數：%d）", fg_level, fg_score)

    # === Layer 2 & 3: 逐股分析 + Decision Engine（並行） ===
    all_stocks = repo.find_active_stocks(session)
    stock_map: dict[str, Stock] = {s.ticker: s for s in all_stocks}
    logger.info("掃描對象：%d 檔股票。", len(all_stocks))

    def _analyze_single_stock(stock: Stock, mkt_status: str) -> dict:
        """單一股票的分析邏輯（可在 Thread 中執行）。"""
        ticker = stock.ticker
        alerts: list[str] = []

        if stock.category.value in SKIP_MOAT_CATEGORIES:
            moat_not_applicable = t(
                "scan.moat_not_applicable", lang=lang, category=stock.category.value
            )
            moat_result = {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": moat_not_applicable,
            }
        else:
            moat_result = analyze_moat_trend(ticker)
        moat_value = moat_result.get("moat", MoatStatus.NOT_AVAILABLE.value)
        moat_details = moat_result.get("details", "")

        # Cash 類不取得技術訊號
        if stock.category.value in SKIP_SIGNALS_CATEGORIES:
            signals = None
        else:
            signals = get_technical_signals(ticker)
        rsi: float | None = None
        bias: float | None = None
        bias_200: float | None = None
        volume_ratio: float | None = None
        price: float | None = None
        if signals and "error" not in signals:
            rsi = signals.get("rsi")
            bias = signals.get("bias")
            bias_200 = signals.get("bias_200")
            volume_ratio = signals.get("volume_ratio")
            price = signals.get("price")
        elif signals and "error" in signals:
            alerts.append(signals["error"])

        signal = determine_scan_signal(
            moat_value, rsi, bias, bias_200, stock.category.value
        )

        # === Rogue Wave (瘋狗浪) ===
        bias_percentile: float | None = None
        is_rogue_wave = False
        if bias is not None and stock.category.value not in SKIP_SIGNALS_CATEGORIES:
            dist = get_bias_distribution(ticker)
            if dist:
                bias_percentile = compute_bias_percentile(
                    bias, dist["historical_biases"]
                )
            is_rogue_wave = detect_rogue_wave(bias_percentile, volume_ratio)
            if is_rogue_wave:
                alerts.append(
                    t(
                        "scan.rogue_wave_alert",
                        lang=lang,
                        ticker=ticker,
                        bias=round(bias, 1),
                        percentile=round(bias_percentile)
                        if bias_percentile is not None
                        else "N/A",
                        vol_ratio=round(volume_ratio, 1)
                        if volume_ratio is not None
                        else "N/A",
                    )
                )

        if signal == ScanSignal.THESIS_BROKEN:
            alerts.append(
                t(
                    "scan.thesis_broken_alert",
                    lang=lang,
                    ticker=ticker,
                    details=moat_details,
                )
            )
        elif signal == ScanSignal.DEEP_VALUE:
            alerts.append(
                t(
                    "scan.deep_value_alert",
                    lang=lang,
                    ticker=ticker,
                    bias=round(bias, 1),
                    rsi=round(rsi, 1),
                )
            )
        elif signal == ScanSignal.OVERSOLD:
            alerts.append(
                t(
                    "scan.oversold_alert",
                    lang=lang,
                    ticker=ticker,
                    bias=round(bias, 1),
                )
            )
        elif signal == ScanSignal.CONTRARIAN_BUY:
            alerts.append(
                t(
                    "scan.contrarian_buy_alert",
                    lang=lang,
                    ticker=ticker,
                    rsi=round(rsi, 1),
                )
            )
        elif signal == ScanSignal.APPROACHING_BUY:
            alerts.append(
                t(
                    "scan.approaching_buy_alert",
                    lang=lang,
                    ticker=ticker,
                    rsi=round(rsi, 1) if rsi is not None else "N/A",
                    bias=round(bias, 1) if bias is not None else "N/A",
                    bias_200=round(bias_200, 1) if bias_200 is not None else "N/A",
                )
            )
        elif signal == ScanSignal.OVERHEATED:
            alerts.append(
                t(
                    "scan.overheated_alert",
                    lang=lang,
                    ticker=ticker,
                    bias=round(bias, 1),
                )
            )
        elif signal == ScanSignal.CAUTION_HIGH:
            alerts.append(
                t(
                    "scan.caution_high_alert",
                    lang=lang,
                    ticker=ticker,
                    bias=round(bias, 1) if bias is not None else "N/A",
                    rsi=round(rsi, 1) if rsi is not None else "N/A",
                )
            )
        elif signal == ScanSignal.WEAKENING:
            alerts.append(
                t(
                    "scan.weakening_alert",
                    lang=lang,
                    ticker=ticker,
                    bias=round(bias, 1),
                    rsi=round(rsi, 1),
                )
            )

        # Volume confidence qualifier: append to the last signal alert (if any).
        # Excluded: NORMAL (no alert), THESIS_BROKEN (fundamental signal, volume irrelevant).
        if (
            alerts
            and volume_ratio is not None
            and signal
            not in (
                ScanSignal.NORMAL,
                ScanSignal.THESIS_BROKEN,
            )
        ):
            if volume_ratio >= VOLUME_SURGE_THRESHOLD:
                alerts[-1] += " " + t("scan.volume_surge", lang=lang)
            elif volume_ratio <= VOLUME_THIN_THRESHOLD:
                alerts[-1] += " " + t("scan.volume_thin", lang=lang)

        if moat_value == MoatStatus.STABLE.value and moat_details:
            alerts.append(
                t(
                    "scan.moat_stable_alert",
                    lang=lang,
                    ticker=ticker,
                    details=moat_details,
                )
            )
        if moat_value == MoatStatus.NOT_AVAILABLE.value and moat_details:
            alerts.append(
                t(
                    "scan.moat_unavailable_alert",
                    lang=lang,
                    ticker=ticker,
                    details=moat_details,
                )
            )

        logger.info(
            "%s → signal=%s, moat=%s, rsi=%s, bias=%s, vol_ratio=%s",
            ticker,
            signal.value,
            moat_value,
            rsi,
            bias,
            volume_ratio,
        )

        return {
            "ticker": ticker,
            "category": stock.category,
            "signal": signal.value,
            "alerts": alerts,
            "moat": moat_value,
            "bias": bias,
            "volume_ratio": volume_ratio,
            "price": price,
            "rsi": rsi,
            "market_status": market_status_value,
            "bias_percentile": bias_percentile,
            "is_rogue_wave": is_rogue_wave,
        }

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=SCAN_THREAD_POOL_SIZE) as executor:
        futures = {
            executor.submit(_analyze_single_stock, s, market_status_value): s
            for s in all_stocks
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                stock = futures[future]
                logger.error("掃描 %s 失敗：%s", stock.ticker, exc, exc_info=True)

    # === 持久化掃描紀錄 ===
    for r in results:
        scan_log = ScanLog(
            stock_ticker=r["ticker"],
            signal=r["signal"],
            market_status=market_status_value,
            market_status_details=market_status_details_value,
            details=json.dumps(r["alerts"], ensure_ascii=False),
        )
        repo.create_scan_log(session, scan_log)
    session.commit()

    # === 檢查自訂價格警報 ===
    _check_price_alerts(session, results, lang)

    # === 差異比對 + 通知 ===
    category_icon = CATEGORY_ICON

    # 比對每檔股票的 current signal vs last_scan_signal
    new_or_changed: list[dict] = []  # signal 從 NORMAL→非 NORMAL，或非 NORMAL 類型改變
    resolved: list[dict] = []  # signal 從非 NORMAL→NORMAL
    signal_updates: dict[str, str] = {}

    for r in results:
        ticker = r["ticker"]
        current_signal = r["signal"]
        stock_obj = stock_map.get(ticker)
        prev_signal = (
            stock_obj.last_scan_signal if stock_obj else ScanSignal.NORMAL.value
        )

        signal_updates[ticker] = current_signal

        if current_signal == prev_signal:
            continue  # 無變化，不通知
        if current_signal != ScanSignal.NORMAL.value:
            new_or_changed.append(r)
        else:
            resolved.append(r)

    # 持久化所有股票的最新 signal（不論是否有變化）
    repo.bulk_update_scan_signals(session, signal_updates)

    has_changes = bool(new_or_changed) or bool(resolved)

    if has_changes:
        logger.warning(
            "掃描差異：%d 檔新增/變更，%d 檔已恢復。",
            len(new_or_changed),
            len(resolved),
        )
        header = t(
            "scan.alert_header",
            lang=lang,
            market_status=market_status_value,
            fg_label=fg_label,
        )

        # 新增/惡化的股票依類別分組
        body_parts: list[str] = []
        if new_or_changed:
            grouped: dict[str, list[str]] = {}
            for r in new_or_changed:
                cat = r.get("category", DEFAULT_IMPORT_CATEGORY)
                cat_value = cat.value if hasattr(cat, "value") else str(cat)
                grouped.setdefault(cat_value, []).extend(r["alerts"])

            for cat_key in CATEGORY_DISPLAY_ORDER:
                if cat_key in grouped:
                    icon = category_icon.get(cat_key, "")
                    label = CATEGORY_LABEL.get(cat_key, cat_key)
                    section_header = f"\n{icon} <b>{label}</b>"
                    section_lines = "\n".join(grouped[cat_key])
                    body_parts.append(f"{section_header}\n{section_lines}")

        # 恢復正常的股票
        if resolved:
            resolved_tickers = ", ".join(r["ticker"] for r in resolved)
            resolved_section = t(
                "scan.resolved_section", lang=lang, tickers=resolved_tickers
            )
            body_parts.append(f"\n{resolved_section}")

        if is_notification_enabled(session, "scan_alerts"):
            send_telegram_message_dual(header + "\n".join(body_parts), session)
        else:
            logger.info("掃描訊號通知已被使用者停用，跳過發送。")
    else:
        logger.info("掃描完成，訊號無變化，跳過通知。")

    return {
        "market_status": market_sentiment,
        "fear_greed": fear_greed,
        "results": results,
    }


def _check_price_alerts(session: Session, results: list[dict], lang: str) -> None:
    """檢查所有啟用中的自訂價格警報，觸發時發送 Telegram 通知。"""
    all_alerts = repo.find_all_active_alerts(session)
    if not all_alerts:
        return

    # 建立 ticker → result 快查表
    result_map = {r["ticker"]: r for r in results}
    triggered_msgs: list[str] = []
    now = datetime.now(timezone.utc)

    for alert in all_alerts:
        r = result_map.get(alert.stock_ticker)
        if not r:
            continue

        # 取得指標值
        metric_value: float | None = None
        if alert.metric == "rsi":
            metric_value = r.get("rsi")
        elif alert.metric == "price":
            metric_value = r.get("price")
        elif alert.metric == "bias":
            metric_value = r.get("bias")

        if metric_value is None:
            continue

        # 比較
        triggered = False
        if alert.operator == "lt" and metric_value < alert.threshold:
            triggered = True
        elif alert.operator == "gt" and metric_value > alert.threshold:
            triggered = True

        if not triggered:
            continue

        # 冷卻檢查
        if alert.last_triggered_at:
            cooldown = timedelta(hours=PRICE_ALERT_COOLDOWN_HOURS)
            if now - alert.last_triggered_at < cooldown:
                continue

        # 觸發
        alert.last_triggered_at = now
        session.add(alert)
        op_label = "<" if alert.operator == "lt" else ">"
        triggered_msgs.append(
            f"🔔 {alert.stock_ticker} {alert.metric}={metric_value} "
            f"{op_label} {alert.threshold}"
        )

    if triggered_msgs:
        session.commit()
        if is_notification_enabled(session, "price_alerts"):
            msg = (
                t("scan.price_alert_header", lang=lang)
                + "\n\n"
                + "\n".join(triggered_msgs)
            )
            send_telegram_message_dual(msg, session)
            logger.warning("觸發 %d 個自訂價格警報。", len(triggered_msgs))
        else:
            logger.info("價格警報通知已被使用者停用，跳過發送。")


# ===========================================================================
# Scan History Service
# ===========================================================================


def get_scan_history(
    session: Session, ticker: str, limit: int = SCAN_HISTORY_DEFAULT_LIMIT
) -> list[dict]:
    """取得指定股票的掃描歷史。"""
    stock = _get_stock_or_raise(session, ticker)
    logs = repo.find_scan_history(session, stock.ticker, limit)
    return [
        {
            "signal": log.signal,
            "market_status": log.market_status,
            "details": log.details,
            "scanned_at": log.scanned_at.isoformat() if log.scanned_at else None,
        }
        for log in logs
    ]


def get_latest_scan_logs(
    session: Session, limit: int = LATEST_SCAN_LOGS_DEFAULT_LIMIT
) -> list[dict]:
    """取得最近的掃描紀錄。"""
    logs = repo.find_latest_scan_logs(session, limit)
    return [
        {
            "ticker": log.stock_ticker,
            "signal": log.signal,
            "market_status": log.market_status,
            "details": log.details,
            "scanned_at": log.scanned_at.isoformat() if log.scanned_at else None,
        }
        for log in logs
    ]


# ===========================================================================
# Price Alert Service
# ===========================================================================


def create_price_alert(
    session: Session,
    ticker: str,
    metric: str,
    operator: str,
    threshold: float,
) -> dict:
    """建立自訂價格警報。"""
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    lang = get_user_language(session)

    alert = PriceAlert(
        stock_ticker=ticker_upper,
        metric=metric,
        operator=operator,
        threshold=threshold,
    )
    saved = repo.create_price_alert(session, alert)
    op_label = "<" if operator == "lt" else ">"
    return {
        "message": t(
            "scan.alert_created",
            lang=lang,
            ticker=ticker_upper,
            metric=metric,
            op=op_label,
            threshold=threshold,
        ),
        "id": saved.id,
    }


def list_price_alerts(session: Session, ticker: str) -> list[dict]:
    """取得指定股票的所有警報。"""
    alerts = repo.find_all_alerts_for_stock(session, ticker.upper())
    return [
        {
            "id": a.id,
            "metric": a.metric,
            "operator": a.operator,
            "threshold": a.threshold,
            "is_active": a.is_active,
            "last_triggered_at": (
                a.last_triggered_at.isoformat() if a.last_triggered_at else None
            ),
        }
        for a in alerts
    ]


def delete_price_alert(session: Session, alert_id: int) -> dict:
    """刪除價格警報。"""
    lang = get_user_language(session)
    alert = repo.find_price_alert_by_id(session, alert_id)
    if not alert:
        return {"message": t("scan.alert_not_found", lang=lang)}
    repo.delete_price_alert(session, alert)
    return {"message": t("scan.alert_deleted", lang=lang)}


def toggle_price_alert(session: Session, alert_id: int) -> dict:
    """切換價格警報啟用狀態（active ↔ inactive）。"""
    lang = get_user_language(session)
    alert = repo.find_price_alert_by_id(session, alert_id)
    if not alert:
        return {"message": t("scan.alert_not_found", lang=lang)}
    alert.is_active = not alert.is_active
    session.add(alert)
    session.commit()
    key = "scan.alert_resumed" if alert.is_active else "scan.alert_paused"
    return {"message": t(key, lang=lang), "is_active": alert.is_active}
