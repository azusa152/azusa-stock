"""
Application — Service Layer (Use Cases)。
編排業務流程，協調 Repository 與 Infrastructure Adapter。
不包含 HTTP/框架邏輯。
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from domain.analysis import determine_scan_signal
from domain.constants import (
    CATEGORY_DISPLAY_ORDER,
    CATEGORY_ICON,
    DEFAULT_IMPORT_CATEGORY,
    DEFAULT_USER_ID,
    DEFAULT_WEBHOOK_THESIS,
    FX_HIGH_CONCENTRATION_PCT,
    FX_MEDIUM_CONCENTRATION_PCT,
    FX_SIGNIFICANT_CHANGE_PCT,
    LATEST_SCAN_LOGS_DEFAULT_LIMIT,
    PRICE_ALERT_COOLDOWN_HOURS,
    REMOVAL_REASON_UNKNOWN,
    SCAN_HISTORY_DEFAULT_LIMIT,
    SCAN_THREAD_POOL_SIZE,
    SKIP_MOAT_CATEGORIES,
    SKIP_SIGNALS_CATEGORIES,
    WEBHOOK_ACTION_REGISTRY,
    WEBHOOK_MISSING_TICKER,
    WEEKLY_DIGEST_LOOKBACK_DAYS,
    XRAY_SINGLE_STOCK_WARN_PCT,
    XRAY_SKIP_CATEGORIES,
)
from domain.entities import PriceAlert, RemovalLog, ScanLog, Stock, ThesisLog
from domain.enums import CATEGORY_LABEL, MarketSentiment, MoatStatus, ScanSignal, StockCategory
from infrastructure import repositories as repo
from infrastructure.market_data import (
    analyze_market_sentiment,
    analyze_moat_trend,
    get_etf_top_holdings,
    get_exchange_rates,
    get_forex_history,
    get_technical_signals,
)
from infrastructure.notification import send_telegram_message_dual
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tag 轉換工具
# ---------------------------------------------------------------------------


def _tags_to_str(tags: list[str]) -> str:
    """將標籤列表轉為逗號分隔字串存入 DB。"""
    return ",".join(t.strip() for t in tags if t.strip())


def _str_to_tags(s: str) -> list[str]:
    """將 DB 中的逗號分隔字串轉為標籤列表。"""
    return [t.strip() for t in s.split(",") if t.strip()] if s else []


# ===========================================================================
# Stock Service
# ===========================================================================


class StockNotFoundError(Exception):
    """股票不存在。"""


class StockAlreadyExistsError(Exception):
    """股票已存在。"""


class StockAlreadyInactiveError(Exception):
    """股票已是停用狀態。"""


class StockAlreadyActiveError(Exception):
    """股票已是啟用狀態。"""


class CategoryUnchangedError(Exception):
    """分類相同，無需變更。"""


# ---------------------------------------------------------------------------
# 共用內部工具
# ---------------------------------------------------------------------------


def _get_stock_or_raise(session: Session, ticker: str) -> Stock:
    """查詢股票，不存在時拋出 StockNotFoundError。"""
    upper = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {upper}。")
    return stock


def _append_thesis_log(
    session: Session,
    ticker: str,
    content: str,
    tags: str = "",
) -> ThesisLog:
    """建立新版觀點紀錄（自動遞增版本號）。"""
    max_version = repo.get_max_thesis_version(session, ticker)
    log = ThesisLog(
        stock_ticker=ticker,
        content=content,
        tags=tags,
        version=max_version + 1,
    )
    repo.create_thesis_log(session, log)
    return log


def create_stock(
    session: Session,
    ticker: str,
    category: StockCategory,
    thesis: str,
    tags: list[str] | None = None,
) -> Stock:
    """
    新增股票到追蹤清單，同時建立第一筆觀點紀錄。
    """
    ticker_upper = ticker.upper()
    tags = tags or []
    tags_str = _tags_to_str(tags)
    logger.info("新增股票：%s（分類：%s，標籤：%s）", ticker_upper, category.value, tags)

    existing = repo.find_stock_by_ticker(session, ticker_upper)
    if existing:
        raise StockAlreadyExistsError(f"股票 {ticker_upper} 已存在追蹤清單中。")

    stock = Stock(
        ticker=ticker_upper,
        category=category,
        current_thesis=thesis,
        current_tags=tags_str,
        is_active=True,
    )
    session.add(stock)

    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=thesis,
        tags=tags_str,
        version=1,
    )
    repo.create_thesis_log(session, thesis_log)

    session.commit()
    session.refresh(stock)

    logger.info("股票 %s 已成功新增至追蹤清單。", ticker_upper)
    return stock


def list_active_stocks(session: Session) -> list[dict]:
    """取得所有啟用中的追蹤股票（僅 DB 資料，不含技術訊號）。"""
    logger.info("取得所有追蹤股票清單...")
    stocks = repo.find_active_stocks(session)
    logger.info("共 %d 檔追蹤中股票。", len(stocks))

    return [
        {
            "ticker": stock.ticker,
            "category": stock.category,
            "current_thesis": stock.current_thesis,
            "current_tags": _str_to_tags(stock.current_tags),
            "display_order": stock.display_order,
            "is_active": stock.is_active,
        }
        for stock in stocks
    ]


def update_stock_category(session: Session, ticker: str, new_category: StockCategory) -> dict:
    """
    切換股票分類，並在觀點歷史中記錄變更。
    """
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    logger.info("分類變更請求：%s → %s", ticker_upper, new_category.value)

    old_category = stock.category
    if old_category == new_category:
        old_label = CATEGORY_LABEL.get(old_category.value, old_category.value)
        raise CategoryUnchangedError(f"股票 {ticker_upper} 已經是 {old_label} 分類。")

    stock.category = new_category
    repo.update_stock(session, stock)

    old_label = CATEGORY_LABEL.get(old_category.value, old_category.value)
    new_label = CATEGORY_LABEL.get(new_category.value, new_category.value)
    _append_thesis_log(session, ticker_upper, f"[分類變更] {old_label} → {new_label}")

    session.commit()
    logger.info("股票 %s 分類已從 %s 變更為 %s。", ticker_upper, old_label, new_label)

    return {
        "message": f"✅ {ticker_upper} 分類已從「{old_label}」變更為「{new_label}」。",
        "old_category": old_category.value,
        "new_category": new_category.value,
    }


def deactivate_stock(session: Session, ticker: str, reason: str) -> dict:
    """
    移除追蹤股票，記錄移除原因與觀點版控。
    """
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    logger.info("移除追蹤：%s", ticker_upper)

    if not stock.is_active:
        raise StockAlreadyInactiveError(f"股票 {ticker_upper} 已經是移除狀態。")

    stock.is_active = False
    repo.update_stock(session, stock)

    removal_log = RemovalLog(stock_ticker=ticker_upper, reason=reason)
    repo.create_removal_log(session, removal_log)

    _append_thesis_log(session, ticker_upper, f"[已移除] {reason}")

    session.commit()
    logger.info("股票 %s 已移除追蹤（原因：%s）。", ticker_upper, reason)

    return {"message": f"✅ {ticker_upper} 已從追蹤清單移除。", "reason": reason}


def reactivate_stock(
    session: Session,
    ticker: str,
    category: StockCategory | None = None,
    thesis: str | None = None,
) -> dict:
    """
    重新啟用已移除的股票。可選擇性更新分類與觀點。
    """
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    logger.info("重新啟用追蹤：%s", ticker_upper)

    if stock.is_active:
        raise StockAlreadyActiveError(f"股票 {ticker_upper} 已經是啟用狀態。")

    stock.is_active = True
    stock.last_scan_signal = ScanSignal.NORMAL.value
    if category:
        stock.category = category
    repo.update_stock(session, stock)

    _append_thesis_log(session, ticker_upper, thesis or "[重新啟用追蹤]")

    if thesis:
        stock.current_thesis = thesis
        repo.update_stock(session, stock)

    session.commit()
    logger.info("股票 %s 已重新啟用追蹤。", ticker_upper)

    return {"message": f"✅ {ticker_upper} 已重新啟用追蹤。"}


def export_stocks(session: Session) -> list[dict]:
    """匯出所有啟用中股票（精簡格式，適用於 JSON 下載與匯入）。"""
    logger.info("匯出所有追蹤股票...")
    stocks = repo.find_active_stocks(session)
    return [
        {
            "ticker": stock.ticker,
            "category": stock.category.value,
            "thesis": stock.current_thesis,
            "tags": _str_to_tags(stock.current_tags),
        }
        for stock in stocks
    ]


def update_display_order(session: Session, ordered_tickers: list[str]) -> dict:
    """批次更新股票顯示順位（委託 Repository 執行）。"""
    logger.info("更新顯示順位，共 %d 檔股票。", len(ordered_tickers))
    upper_tickers = [t.upper() for t in ordered_tickers]
    repo.bulk_update_display_order(session, upper_tickers)
    return {"message": f"✅ 已更新 {len(ordered_tickers)} 檔股票的顯示順位。"}


def list_removed_stocks(session: Session) -> list[dict]:
    """取得所有已移除的股票，含最新移除原因（批次查詢，避免 N+1）。"""
    logger.info("取得已移除股票清單...")
    stocks = repo.find_inactive_stocks(session)

    # 一次性取得所有已移除股票的最新移除紀錄
    tickers = [s.ticker for s in stocks]
    removal_map = repo.find_latest_removals_batch(session, tickers)

    results: list[dict] = []
    for stock in stocks:
        latest_removal = removal_map.get(stock.ticker)
        results.append({
            "ticker": stock.ticker,
            "category": stock.category,
            "current_thesis": stock.current_thesis,
            "removal_reason": latest_removal.reason if latest_removal else REMOVAL_REASON_UNKNOWN,
            "removed_at": (
                latest_removal.created_at.isoformat()
                if latest_removal and latest_removal.created_at
                else None
            ),
        })

    logger.info("共 %d 檔已移除股票。", len(results))
    return results


def get_removal_history(session: Session, ticker: str) -> list[dict]:
    """取得指定股票的完整移除紀錄歷史。"""
    stock = _get_stock_or_raise(session, ticker)
    logs = repo.find_removal_history(session, stock.ticker)
    return [
        {
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ===========================================================================
# Thesis Service
# ===========================================================================


def add_thesis(
    session: Session,
    ticker: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """為指定股票新增觀點，自動遞增版本號。"""
    stock = _get_stock_or_raise(session, ticker)
    ticker_upper = stock.ticker
    tags = tags or []
    tags_str = _tags_to_str(tags)
    logger.info("更新觀點：%s（標籤：%s）", ticker_upper, tags)

    thesis_log = _append_thesis_log(session, ticker_upper, content, tags_str)
    new_version = thesis_log.version

    stock.current_thesis = content
    stock.current_tags = tags_str
    repo.update_stock(session, stock)
    session.commit()

    logger.info("股票 %s 觀點已更新至第 %d 版。", ticker_upper, new_version)

    return {
        "message": f"✅ {ticker_upper} 觀點已更新至第 {new_version} 版。",
        "version": new_version,
        "content": content,
        "tags": tags,
    }


def get_thesis_history(session: Session, ticker: str) -> list[dict]:
    """取得指定股票的完整觀點版控歷史。"""
    stock = _get_stock_or_raise(session, ticker)
    logs = repo.find_thesis_history(session, stock.ticker)
    return [
        {
            "version": log.version,
            "content": log.content,
            "tags": _str_to_tags(log.tags),
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


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
        header = f"🔔 <b>Folio 掃描（差異通知）</b>\n市場情緒：{market_status_value}\n"

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

        send_telegram_message_dual(header + "\n".join(body_parts), session)
    else:
        logger.info("掃描完成，訊號無變化，跳過通知。")

    return {"market_status": market_sentiment, "results": results}


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
        msg = "⚡ <b>自訂價格警報觸發</b>\n\n" + "\n".join(triggered_msgs)
        send_telegram_message_dual(msg, session)
        logger.warning("觸發 %d 個自訂價格警報。", len(triggered_msgs))


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

    # 組合訊息
    parts: list[str] = [
        f"📊 <b>Folio 每週摘要</b>\n",
        f"🏥 投資組合健康分數：<b>{health_score}%</b>（{normal_count}/{total} 正常）\n",
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
    send_telegram_message_dual(message, session)
    logger.info("每週摘要已發送。")

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

    lines: list[str] = [f"Folio — Health: {health}%", ""]

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


# ===========================================================================
# Import Service
# ===========================================================================


def import_stocks(session: Session, stock_list: list[dict]) -> dict:
    """
    批次匯入股票（upsert 邏輯）。
    新股票建立，已存在的更新觀點與標籤。
    """
    logger.info("批次匯入 %d 筆股票...", len(stock_list))
    created = 0
    updated = 0
    errors: list[str] = []

    for item in stock_list:
        ticker = item.get("ticker", "").strip().upper()
        category_str = item.get("category", DEFAULT_IMPORT_CATEGORY)
        thesis = item.get("thesis", "") or item.get("initial_thesis", "")
        tags = item.get("tags", [])

        if not ticker:
            errors.append("缺少 ticker 欄位")
            continue

        try:
            category = StockCategory(category_str)
        except ValueError:
            errors.append(f"{ticker}: 無效分類 {category_str}")
            continue

        existing = repo.find_stock_by_ticker(session, ticker)
        tags_str = _tags_to_str(tags)

        if existing:
            # Upsert: 更新觀點與標籤
            if thesis:
                _append_thesis_log(session, ticker, thesis, tags_str)
                existing.current_thesis = thesis
            if tags:
                existing.current_tags = tags_str
            existing.category = category
            repo.update_stock(session, existing)
            updated += 1
        else:
            # 新增
            stock = Stock(
                ticker=ticker,
                category=category,
                current_thesis=thesis,
                current_tags=tags_str,
                is_active=True,
            )
            session.add(stock)
            thesis_log = ThesisLog(
                stock_ticker=ticker,
                content=thesis,
                tags=tags_str,
                version=1,
            )
            repo.create_thesis_log(session, thesis_log)
            created += 1

    session.commit()
    logger.info("匯入完成：新增 %d，更新 %d，錯誤 %d。", created, updated, len(errors))

    return {
        "message": f"✅ 匯入完成：新增 {created}，更新 {updated}，錯誤 {len(errors)}。",
        "created": created,
        "updated": updated,
        "errors": errors,
    }


# ===========================================================================
# Moat Service（Bond / Cash 不適用）
# ===========================================================================


def get_moat_for_ticker(session: Session, ticker: str) -> dict:
    """取得指定股票的護城河趨勢。Bond / Cash 類別直接回傳 N/A。"""
    upper_ticker = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper_ticker)
    if stock and stock.category.value in SKIP_MOAT_CATEGORIES:
        return {"ticker": upper_ticker, "moat": "N/A", "details": f"{stock.category.value} 不適用護城河分析"}
    return analyze_moat_trend(upper_ticker)


# ===========================================================================
# Webhook Service (for OpenClaw / AI agents)
# ===========================================================================


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


# ===========================================================================
# Asset Allocation — 再平衡分析
# ===========================================================================


def calculate_rebalance(session: Session, display_currency: str = "USD") -> dict:
    """
    計算再平衡分析：比較目標配置與實際持倉。
    1. 讀取啟用中的 UserInvestmentProfile（目標配置）
    2. 讀取所有 Holding（實際持倉）
    3. 取得匯率，將所有持倉轉換為 display_currency
    4. 對非現金持倉查詢即時價格
    5. 委託 domain.rebalance 純函式計算偏移與建議
    """
    import json as _json

    from domain.entities import Holding, UserInvestmentProfile
    from domain.rebalance import calculate_rebalance as _pure_rebalance
    from infrastructure.market_data import get_technical_signals

    # 1) 取得目標配置
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()

    if not profile:
        raise StockNotFoundError("尚未設定投資組合目標配置，請先選擇投資人格。")

    target_config: dict[str, float] = _json.loads(profile.config)

    # 2) 取得所有持倉
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()

    if not holdings:
        raise StockNotFoundError("尚未輸入任何持倉，請先新增資產。")

    # 3) 取得匯率：收集所有持倉幣別，批次取得相對 display_currency 的匯率
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)
    logger.info(
        "匯率轉換（→ %s）：%s",
        display_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    # 4) 計算各持倉的市值（已換算為 display_currency），同時建立個股明細
    category_values: dict[str, float] = {}
    ticker_agg: dict[str, dict] = {}

    for h in holdings:
        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        fx = fx_rates.get(h.currency, 1.0)
        price: float | None = None

        if h.is_cash:
            # 現金持倉：quantity 即面額，需以匯率換算
            market_value = h.quantity * fx
            price = 1.0
        else:
            signals = get_technical_signals(h.ticker)
            price = signals.get("price") if signals else None
            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

        category_values[cat] = category_values.get(cat, 0.0) + market_value

        # Aggregate by ticker (merge across brokers)
        key = h.ticker
        if key not in ticker_agg:
            ticker_agg[key] = {
                "category": cat,
                "currency": h.currency,
                "qty": 0.0,
                "mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
            }
        ticker_agg[key]["qty"] += h.quantity
        ticker_agg[key]["mv"] += market_value
        if h.cost_basis is not None:
            ticker_agg[key]["cost_sum"] += h.cost_basis * h.quantity
            ticker_agg[key]["cost_qty"] += h.quantity

    # 5) 委託 domain 純函式計算
    result = _pure_rebalance(category_values, target_config)

    # 6) 建立個股明細（含佔比）
    total_value = result["total_value"]
    holdings_detail = []
    for ticker, agg in ticker_agg.items():
        avg_cost = (
            round(agg["cost_sum"] / agg["cost_qty"], 2)
            if agg["cost_qty"] > 0
            else None
        )
        weight_pct = (
            round((agg["mv"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        cur_price = agg["price"]
        holdings_detail.append(
            {
                "ticker": ticker,
                "category": agg["category"],
                "currency": agg["currency"],
                "quantity": round(agg["qty"], 4),
                "market_value": round(agg["mv"], 2),
                "weight_pct": weight_pct,
                "avg_cost": avg_cost,
                "current_price": (
                    round(cur_price, 2)
                    if cur_price is not None and isinstance(cur_price, (int, float))
                    else None
                ),
            }
        )

    # Sort by weight descending (largest positions first)
    holdings_detail.sort(key=lambda x: x["weight_pct"], reverse=True)
    result["holdings_detail"] = holdings_detail
    result["display_currency"] = display_currency

    # 7) X-Ray: 穿透式持倉分析（解析 ETF 成分股，計算真實曝險）
    xray_map: dict[str, dict] = {}  # symbol -> {direct, indirect, sources, name}

    for ticker, agg in ticker_agg.items():
        cat = agg["category"]
        mv = agg["mv"]
        if cat in XRAY_SKIP_CATEGORIES or mv <= 0:
            continue

        # 嘗試取得 ETF 成分股
        constituents = get_etf_top_holdings(ticker)
        if constituents:
            # 此 ticker 是 ETF — 計算間接曝險
            for c in constituents:
                sym = c["symbol"]
                weight = c["weight"]
                indirect_mv = mv * weight
                if sym not in xray_map:
                    xray_map[sym] = {
                        "name": c.get("name", ""),
                        "direct": 0.0,
                        "indirect": 0.0,
                        "sources": [],
                    }
                xray_map[sym]["indirect"] += indirect_mv
                src_pct = round(weight * 100, 2)
                xray_map[sym]["sources"].append(f"{ticker} ({src_pct}%)")
        else:
            # 非 ETF — 記錄為直接持倉
            if ticker not in xray_map:
                xray_map[ticker] = {
                    "name": "",
                    "direct": 0.0,
                    "indirect": 0.0,
                    "sources": [],
                }
            xray_map[ticker]["direct"] += mv

    # 組合 X-Ray 結果
    xray_entries = []
    for symbol, data in xray_map.items():
        total_val = data["direct"] + data["indirect"]
        if total_val <= 0:
            continue
        direct_pct = round((data["direct"] / total_value) * 100, 2) if total_value > 0 else 0.0
        indirect_pct = round((data["indirect"] / total_value) * 100, 2) if total_value > 0 else 0.0
        total_pct = round((total_val / total_value) * 100, 2) if total_value > 0 else 0.0
        xray_entries.append(
            {
                "symbol": symbol,
                "name": data["name"],
                "direct_value": round(data["direct"], 2),
                "direct_weight_pct": direct_pct,
                "indirect_value": round(data["indirect"], 2),
                "indirect_weight_pct": indirect_pct,
                "total_value": round(total_val, 2),
                "total_weight_pct": total_pct,
                "indirect_sources": data["sources"],
            }
        )

    xray_entries.sort(key=lambda x: x["total_weight_pct"], reverse=True)
    result["xray"] = xray_entries
    result["calculated_at"] = datetime.now(timezone.utc).isoformat()

    return result


def send_xray_warnings(
    xray_entries: list[dict],
    display_currency: str,
    session: Session,
) -> list[str]:
    """
    檢查 X-Ray 結果，對超過單一標的風險門檻的持倉發送 Telegram 警告。
    回傳已發送的警告訊息列表。
    """
    warnings: list[str] = []
    for entry in xray_entries:
        total_pct = entry.get("total_weight_pct", 0.0)
        indirect_val = entry.get("indirect_value", 0.0)
        if total_pct > XRAY_SINGLE_STOCK_WARN_PCT and indirect_val > 0:
            symbol = entry["symbol"]
            direct_pct = entry.get("direct_weight_pct", 0.0)
            sources = ", ".join(entry.get("indirect_sources", []))
            msg = (
                f"⚠️ X-Ray 警告：{symbol} 直接持倉佔 {direct_pct:.1f}%，"
                f"加上 ETF 間接曝險（{sources}），"
                f"真實曝險已達 {total_pct:.1f}%，"
                f"超過單一標的風險建議值 {XRAY_SINGLE_STOCK_WARN_PCT:.0f}%。"
            )
            warnings.append(msg)

    if warnings:
        full_msg = "🔬 穿透式持倉 X-Ray 分析\n\n" + "\n\n".join(warnings)
        try:
            send_telegram_message_dual(full_msg, session)
            logger.info("已發送 X-Ray 警告（%d 筆）", len(warnings))
        except Exception as e:
            logger.warning("X-Ray Telegram 警告發送失敗：%s", e)

    return warnings


# ===========================================================================
# Currency Exposure Monitor
# ===========================================================================


def calculate_currency_exposure(session: Session, home_currency: str | None = None) -> dict:
    """
    計算匯率曝險分析：
    1. 讀取使用者 Profile 的 home_currency（或使用參數覆寫）
    2. 將所有持倉按幣別分組，計算以本幣計價的市值
    3. 偵測近期匯率變動
    4. 產出風險等級與建議
    """
    from domain.entities import Holding, UserInvestmentProfile

    # 1) 決定本幣
    if not home_currency:
        profile = session.exec(
            select(UserInvestmentProfile)
            .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
            .where(UserInvestmentProfile.is_active == True)  # noqa: E712
        ).first()
        home_currency = profile.home_currency if profile else "TWD"

    # 2) 取得所有持倉
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()

    if not holdings:
        return {
            "home_currency": home_currency,
            "total_value_home": 0.0,
            "breakdown": [],
            "non_home_pct": 0.0,
            "cash_breakdown": [],
            "cash_non_home_pct": 0.0,
            "total_cash_home": 0.0,
            "fx_movements": [],
            "risk_level": "low",
            "advice": ["尚無持倉資料。"],
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    # 3) 取得匯率（all currencies → home_currency）
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(home_currency, holding_currencies)
    logger.info("匯率曝險分析 → %s：%s", home_currency, {k: round(v, 4) for k, v in fx_rates.items()})

    # 4) 按幣別分組計算市值（以本幣計價）— 同時追蹤現金部位
    currency_values: dict[str, float] = {}
    cash_currency_values: dict[str, float] = {}
    for h in holdings:
        fx = fx_rates.get(h.currency, 1.0)
        if h.is_cash:
            market_value = h.quantity * fx
            cash_currency_values[h.currency] = (
                cash_currency_values.get(h.currency, 0.0) + market_value
            )
        else:
            signals = get_technical_signals(h.ticker)
            price = signals.get("price") if signals else None
            if price is None:
                # 無法取得價格，使用成本估算
                price = h.cost_basis or 0.0
            market_value = h.quantity * price * fx

        currency_values[h.currency] = currency_values.get(h.currency, 0.0) + market_value

    total_value_home = sum(currency_values.values())
    total_cash_home = sum(cash_currency_values.values())

    # 5) 建立幣別分佈（全資產）
    breakdown = []
    for cur, val in sorted(currency_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / total_value_home) * 100, 2) if total_value_home > 0 else 0.0
        breakdown.append({
            "currency": cur,
            "value": round(val, 2),
            "percentage": pct,
            "is_home": cur == home_currency,
        })

    non_home_pct = round(
        sum(b["percentage"] for b in breakdown if not b["is_home"]),
        2,
    )

    # 5b) 建立現金幣別分佈
    cash_breakdown = []
    for cur, val in sorted(cash_currency_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / total_cash_home) * 100, 2) if total_cash_home > 0 else 0.0
        cash_breakdown.append({
            "currency": cur,
            "value": round(val, 2),
            "percentage": pct,
            "is_home": cur == home_currency,
        })

    cash_non_home_pct = round(
        sum(b["percentage"] for b in cash_breakdown if not b["is_home"]),
        2,
    )

    # 6) 偵測近期匯率變動（非本幣 → 本幣）
    fx_movements = []
    non_home_currencies = [cur for cur in currency_values if cur != home_currency]
    for cur in non_home_currencies:
        history = get_forex_history(cur, home_currency)
        if len(history) >= 2:
            first_close = history[0]["close"]
            last_close = history[-1]["close"]
            if first_close > 0:
                change_pct = round(((last_close - first_close) / first_close) * 100, 2)
                direction = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
                fx_movements.append({
                    "pair": f"{cur}/{home_currency}",
                    "current_rate": last_close,
                    "change_pct": change_pct,
                    "direction": direction,
                })

    # 7) 風險等級
    if non_home_pct >= FX_HIGH_CONCENTRATION_PCT:
        risk_level = "high"
    elif non_home_pct >= FX_MEDIUM_CONCENTRATION_PCT:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 8) 建議（包含現金部位資訊）
    advice = _generate_fx_advice(
        home_currency,
        breakdown,
        non_home_pct,
        risk_level,
        fx_movements,
        cash_breakdown=cash_breakdown,
        cash_non_home_pct=cash_non_home_pct,
        total_cash_home=total_cash_home,
    )

    return {
        "home_currency": home_currency,
        "total_value_home": round(total_value_home, 2),
        "breakdown": breakdown,
        "non_home_pct": non_home_pct,
        "cash_breakdown": cash_breakdown,
        "cash_non_home_pct": cash_non_home_pct,
        "total_cash_home": round(total_cash_home, 2),
        "fx_movements": fx_movements,
        "risk_level": risk_level,
        "advice": advice,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def _generate_fx_advice(
    home_currency: str,
    breakdown: list[dict],
    non_home_pct: float,
    risk_level: str,
    fx_movements: list[dict],
    *,
    cash_breakdown: list[dict] | None = None,
    cash_non_home_pct: float = 0.0,
    total_cash_home: float = 0.0,
) -> list[str]:
    """根據匯率曝險分析結果產出建議文字。"""
    advice: list[str] = []

    # 集中度建議
    if risk_level == "high":
        top_foreign = [b for b in breakdown if not b["is_home"]]
        if top_foreign:
            top_cur = top_foreign[0]["currency"]
            top_pct = top_foreign[0]["percentage"]
            advice.append(
                f"⚠️ 非本幣（{home_currency}）資產佔比達 {non_home_pct:.1f}%，"
                f"其中 {top_cur} 佔 {top_pct:.1f}%，匯率風險較高。"
                f"建議評估是否需要調整幣別配置以降低單一貨幣曝險。"
            )
    elif risk_level == "medium":
        advice.append(
            f"📊 非本幣資產佔比 {non_home_pct:.1f}%，處於中等水準。"
            f"持續關注主要外幣匯率走勢。"
        )
    else:
        advice.append(
            f"✅ 非本幣資產佔比 {non_home_pct:.1f}%，匯率風險較低。"
        )

    # 現金部位專屬建議
    if cash_breakdown:
        foreign_cash = [b for b in cash_breakdown if not b["is_home"]]
        if foreign_cash and cash_non_home_pct > 0:
            top_cash_cur = foreign_cash[0]["currency"]
            top_cash_val = foreign_cash[0]["value"]
            advice.append(
                f"💵 您的現金部位中，{cash_non_home_pct:.1f}% 為非本幣。"
                f"最大外幣現金為 {top_cash_cur}（約 {top_cash_val:,.0f} {home_currency}），"
                f"受匯率波動直接影響。"
            )

    # 匯率變動建議（含現金金額）
    cash_by_cur = {b["currency"]: b["value"] for b in (cash_breakdown or [])}
    for mv in fx_movements:
        abs_change = abs(mv["change_pct"])
        if abs_change >= FX_SIGNIFICANT_CHANGE_PCT:
            pair = mv["pair"]
            base_cur = pair.split("/")[0]
            cash_amt = cash_by_cur.get(base_cur, 0.0)
            cash_note = (
                f"（其中 {base_cur} 現金約 {cash_amt:,.0f} {home_currency} 直接受影響）"
                if cash_amt > 0
                else ""
            )
            if mv["direction"] == "up":
                advice.append(
                    f"📈 {pair} 近期升值 {mv['change_pct']:+.2f}%，"
                    f"您持有的 {base_cur} 資產以 {home_currency} 計價正在增值。"
                    f"{cash_note}"
                )
            else:
                advice.append(
                    f"📉 {pair} 近期貶值 {mv['change_pct']:+.2f}%，"
                    f"您持有的 {base_cur} 資產以 {home_currency} 計價正在縮水，"
                    f"建議留意是否需要避險。{cash_note}"
                )

    return advice


def check_fx_alerts(session: Session) -> list[str]:
    """
    檢查匯率曝險警報：偵測顯著匯率變動，產出 Telegram 通知文字。
    回傳警報訊息列表（強調現金部位影響）。
    """
    exposure = calculate_currency_exposure(session)
    alerts: list[str] = []

    home_cur = exposure["home_currency"]
    cash_by_cur = {
        b["currency"]: b["value"]
        for b in exposure.get("cash_breakdown", [])
    }

    # 匯率變動警報（含現金金額）
    for mv in exposure.get("fx_movements", []):
        abs_change = abs(mv["change_pct"])
        if abs_change >= FX_SIGNIFICANT_CHANGE_PCT:
            pair = mv["pair"]
            base_cur = pair.split("/")[0]
            cash_amt = cash_by_cur.get(base_cur, 0.0)
            cash_note = (
                f"\n💵 其中 {base_cur} 現金約 {cash_amt:,.0f} {home_cur} 直接受影響。"
                if cash_amt > 0
                else ""
            )
            if mv["direction"] == "up":
                alerts.append(
                    f"📈 {pair} 升值 {mv['change_pct']:+.2f}%（現價 {mv['current_rate']:.4f}）。"
                    f"您的 {base_cur} 購買力上升。{cash_note}"
                )
            else:
                alerts.append(
                    f"📉 {pair} 貶值 {mv['change_pct']:+.2f}%（現價 {mv['current_rate']:.4f}）。"
                    f"您的 {base_cur} 資產以 {home_cur} 計價正在縮水。{cash_note}"
                )

    # 高集中度警報（整體 + 現金）
    non_home_pct = exposure.get("non_home_pct", 0.0)
    cash_non_home_pct = exposure.get("cash_non_home_pct", 0.0)
    if non_home_pct >= FX_HIGH_CONCENTRATION_PCT:
        alerts.append(
            f"⚠️ 非本幣資產佔比高達 {non_home_pct:.1f}%，匯率風險顯著。"
            f"建議評估是否需要降低外幣曝險。"
        )
    if cash_non_home_pct >= FX_HIGH_CONCENTRATION_PCT:
        total_cash = exposure.get("total_cash_home", 0.0)
        alerts.append(
            f"💵 現金部位中非本幣佔 {cash_non_home_pct:.1f}%"
            f"（現金總額約 {total_cash:,.0f} {home_cur}），"
            f"匯率風險直接影響您的流動性資產。"
        )

    return alerts


def send_fx_alerts(session: Session) -> list[str]:
    """
    執行匯率曝險檢查，若有警報則發送 Telegram 通知。
    回傳已發送的警報列表。
    """
    alerts = check_fx_alerts(session)

    if alerts:
        full_msg = "💱 匯率曝險監控\n\n" + "\n\n".join(alerts)
        try:
            send_telegram_message_dual(full_msg, session)
            logger.info("已發送匯率曝險警報（%d 筆）", len(alerts))
        except Exception as e:
            logger.warning("匯率曝險 Telegram 警報發送失敗：%s", e)

    return alerts
