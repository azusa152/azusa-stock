"""
Application — Scan Service：三層漏斗掃描、價格警報、掃描歷史。
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from application.formatters import format_fear_greed_label
from application.stock_service import StockNotFoundError, _get_stock_or_raise
from domain.analysis import determine_scan_signal
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
)
from domain.entities import PriceAlert, ScanLog, Stock
from domain.enums import CATEGORY_LABEL, MarketSentiment, MoatStatus, ScanSignal, StockCategory
from infrastructure import repositories as repo
from infrastructure.market_data import (
    analyze_market_sentiment,
    analyze_moat_trend,
    get_fear_greed_index,
    get_technical_signals,
)
from infrastructure.notification import is_notification_enabled, send_telegram_message_dual
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

    # === Layer 1: 市場情緒 ===
    trend_stocks = repo.find_active_stocks_by_category(session, StockCategory.TREND_SETTER)
    trend_tickers = [s.ticker for s in trend_stocks]
    logger.info("Layer 1 — 風向球股票：%s", trend_tickers)

    market_sentiment = analyze_market_sentiment(trend_tickers)
    market_status_value = market_sentiment.get("status", MarketSentiment.POSITIVE.value)
    market_status_details_value = market_sentiment.get("details", "")
    logger.info("Layer 1 — 市場情緒：%s（%s）", market_status_value, market_status_details_value)

    # === Fear & Greed Index（與 Layer 1 並列的市場概況） ===
    fear_greed = get_fear_greed_index()
    fg_level = fear_greed.get("composite_level", "N/A")
    fg_score = fear_greed.get("composite_score", 50)
    fg_label = format_fear_greed_label(fg_level, fg_score)
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
            moat_result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": f"{stock.category.value} 不適用護城河分析"}
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
        volume_ratio: float | None = None
        price: float | None = None

        if signals and "error" not in signals:
            rsi = signals.get("rsi")
            bias = signals.get("bias")
            volume_ratio = signals.get("volume_ratio")
            price = signals.get("price")
        elif signals and "error" in signals:
            alerts.append(signals["error"])

        signal = determine_scan_signal(moat_value, mkt_status, rsi, bias)

        if signal == ScanSignal.THESIS_BROKEN:
            alerts.append(f"🔴 {ticker} 護城河鬆動！{moat_details}")
        elif signal == ScanSignal.CONTRARIAN_BUY:
            alerts.append(f"🟢 {ticker} 逆勢買入訊號（RSI={rsi}，市場正面）")
        elif signal == ScanSignal.OVERHEATED:
            alerts.append(f"🟠 {ticker} 乖離率過熱（Bias={bias}%）")

        if moat_value == MoatStatus.STABLE.value and moat_details:
            alerts.append(f"🟢 {ticker} {moat_details}")
        if moat_value == MoatStatus.NOT_AVAILABLE.value and moat_details:
            alerts.append(f"⚠️ {ticker} {moat_details}")

        logger.info(
            "%s → signal=%s, moat=%s, rsi=%s, bias=%s, vol_ratio=%s",
            ticker, signal.value, moat_value, rsi, bias, volume_ratio,
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
    _check_price_alerts(session, results)

    # === 差異比對 + 通知 ===
    category_icon = CATEGORY_ICON

    # 比對每檔股票的 current signal vs last_scan_signal
    new_or_changed: list[dict] = []  # signal 從 NORMAL→非 NORMAL，或非 NORMAL 類型改變
    resolved: list[dict] = []        # signal 從非 NORMAL→NORMAL
    signal_updates: dict[str, str] = {}

    for r in results:
        ticker = r["ticker"]
        current_signal = r["signal"]
        stock_obj = stock_map.get(ticker)
        prev_signal = stock_obj.last_scan_signal if stock_obj else ScanSignal.NORMAL.value

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
            len(new_or_changed), len(resolved),
        )
        header = (
            f"🔔 <b>Folio 掃描（差異通知）</b>\n"
            f"市場情緒：{market_status_value} | 恐懼貪婪：{fg_label}\n"
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
            body_parts.append(f"\n✅ <b>已恢復正常</b>\n{resolved_tickers}")

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


def _check_price_alerts(session: Session, results: list[dict]) -> None:
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
            msg = "⚡ <b>自訂價格警報觸發</b>\n\n" + "\n".join(triggered_msgs)
            send_telegram_message_dual(msg, session)
            logger.warning("觸發 %d 個自訂價格警報。", len(triggered_msgs))
        else:
            logger.info("價格警報通知已被使用者停用，跳過發送。")


# ===========================================================================
# Scan History Service
# ===========================================================================


def get_scan_history(session: Session, ticker: str, limit: int = SCAN_HISTORY_DEFAULT_LIMIT) -> list[dict]:
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


def get_latest_scan_logs(session: Session, limit: int = LATEST_SCAN_LOGS_DEFAULT_LIMIT) -> list[dict]:
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

    alert = PriceAlert(
        stock_ticker=ticker_upper,
        metric=metric,
        operator=operator,
        threshold=threshold,
    )
    saved = repo.create_price_alert(session, alert)
    op_label = "<" if operator == "lt" else ">"
    return {
        "message": f"✅ 已建立警報：{ticker_upper} {metric} {op_label} {threshold}",
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
    alert = repo.find_price_alert_by_id(session, alert_id)
    if not alert:
        return {"message": "⚠️ 找不到此警報。"}
    repo.delete_price_alert(session, alert)
    return {"message": "✅ 警報已刪除。"}
