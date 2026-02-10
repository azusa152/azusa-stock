"""
Application — Service Layer (Use Cases)。
編排業務流程，協調 Repository 與 Infrastructure Adapter。
不包含 HTTP/框架邏輯。
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from domain.analysis import determine_scan_signal
from domain.constants import (
    ETF_MOAT_NA_MESSAGE,
    PRICE_ALERT_COOLDOWN_HOURS,
    SCAN_HISTORY_DEFAULT_LIMIT,
    SCAN_THREAD_POOL_SIZE,
    WEEKLY_DIGEST_LOOKBACK_DAYS,
)
from domain.entities import PriceAlert, RemovalLog, ScanLog, Stock, ThesisLog
from domain.enums import CATEGORY_LABEL, MoatStatus, ScanSignal, StockCategory
from infrastructure import repositories as repo
from infrastructure.market_data import (
    analyze_market_sentiment,
    analyze_moat_trend,
    get_technical_signals,
)
from infrastructure.notification import send_telegram_message
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
    ticker_upper = ticker.upper()
    logger.info("分類變更請求：%s → %s", ticker_upper, new_category.value)

    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")

    old_category = stock.category
    if old_category == new_category:
        old_label = CATEGORY_LABEL.get(old_category.value, old_category.value)
        raise CategoryUnchangedError(f"股票 {ticker_upper} 已經是 {old_label} 分類。")

    stock.category = new_category
    repo.update_stock(session, stock)

    # 審計紀錄
    max_version = repo.get_max_thesis_version(session, ticker_upper)
    old_label = CATEGORY_LABEL.get(old_category.value, old_category.value)
    new_label = CATEGORY_LABEL.get(new_category.value, new_category.value)

    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=f"[分類變更] {old_label} → {new_label}",
        version=max_version + 1,
    )
    repo.create_thesis_log(session, thesis_log)

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
    ticker_upper = ticker.upper()
    logger.info("移除追蹤：%s", ticker_upper)

    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")
    if not stock.is_active:
        raise StockAlreadyInactiveError(f"股票 {ticker_upper} 已經是移除狀態。")

    stock.is_active = False
    repo.update_stock(session, stock)

    removal_log = RemovalLog(stock_ticker=ticker_upper, reason=reason)
    repo.create_removal_log(session, removal_log)

    max_version = repo.get_max_thesis_version(session, ticker_upper)
    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=f"[已移除] {reason}",
        version=max_version + 1,
    )
    repo.create_thesis_log(session, thesis_log)

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
    ticker_upper = ticker.upper()
    logger.info("重新啟用追蹤：%s", ticker_upper)

    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")
    if stock.is_active:
        raise StockAlreadyActiveError(f"股票 {ticker_upper} 已經是啟用狀態。")

    stock.is_active = True
    stock.last_scan_signal = "NORMAL"
    if category:
        stock.category = category
    repo.update_stock(session, stock)

    # 觀點版控紀錄
    max_version = repo.get_max_thesis_version(session, ticker_upper)
    thesis_content = thesis or "[重新啟用追蹤]"
    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=thesis_content,
        version=max_version + 1,
    )
    repo.create_thesis_log(session, thesis_log)

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
    """批次更新股票顯示順位（單一 SELECT + 批次寫入）。"""
    logger.info("更新顯示順位，共 %d 檔股票。", len(ordered_tickers))
    upper_tickers = [t.upper() for t in ordered_tickers]
    from sqlmodel import select as sql_select
    from domain.entities import Stock as StockEntity
    stocks = session.exec(
        sql_select(StockEntity).where(StockEntity.ticker.in_(upper_tickers))
    ).all()
    stock_map = {s.ticker: s for s in stocks}
    for index, ticker in enumerate(upper_tickers):
        s = stock_map.get(ticker)
        if s:
            s.display_order = index
    session.commit()
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
            "removal_reason": latest_removal.reason if latest_removal else "未知",
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
    ticker_upper = ticker.upper()

    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")

    logs = repo.find_removal_history(session, ticker_upper)
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
    ticker_upper = ticker.upper()
    tags = tags or []
    tags_str = _tags_to_str(tags)
    logger.info("更新觀點：%s（標籤：%s）", ticker_upper, tags)

    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")

    max_version = repo.get_max_thesis_version(session, ticker_upper)
    new_version = max_version + 1

    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=content,
        tags=tags_str,
        version=new_version,
    )
    repo.create_thesis_log(session, thesis_log)

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
    ticker_upper = ticker.upper()

    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")

    logs = repo.find_thesis_history(session, ticker_upper)
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
    market_status_value = market_sentiment.get("status", "POSITIVE")
    logger.info("Layer 1 — 市場情緒：%s（%s）", market_status_value, market_sentiment.get("details", ""))

    # === Layer 2 & 3: 逐股分析 + Decision Engine（並行） ===
    all_stocks = repo.find_active_stocks(session)
    stock_map: dict[str, Stock] = {s.ticker: s for s in all_stocks}
    logger.info("掃描對象：%d 檔股票。", len(all_stocks))

    def _analyze_single_stock(stock: Stock, mkt_status: str) -> dict:
        """單一股票的分析邏輯（可在 Thread 中執行）。"""
        ticker = stock.ticker
        alerts: list[str] = []

        if stock.category == StockCategory.ETF:
            moat_result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": ETF_MOAT_NA_MESSAGE}
        else:
            moat_result = analyze_moat_trend(ticker)
        moat_value = moat_result.get("moat", MoatStatus.NOT_AVAILABLE.value)
        moat_details = moat_result.get("details", "")

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
            details=json.dumps(r["alerts"], ensure_ascii=False),
        )
        repo.create_scan_log(session, scan_log)
    session.commit()

    # === 檢查自訂價格警報 ===
    _check_price_alerts(session, results)

    # === 差異比對 + 通知 ===
    category_icon = {
        "Trend_Setter": "🌊",
        "Moat": "🏰",
        "Growth": "🚀",
        "ETF": "🧺",
    }

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
        header = f"🔔 <b>Azusa Radar V2 掃描（差異通知）</b>\n市場情緒：{market_status_value}\n"

        # 新增/惡化的股票依類別分組
        body_parts: list[str] = []
        if new_or_changed:
            grouped: dict[str, list[str]] = {}
            for r in new_or_changed:
                cat = r.get("category", "Growth")
                cat_value = cat.value if hasattr(cat, "value") else str(cat)
                grouped.setdefault(cat_value, []).extend(r["alerts"])

            for cat_key in ["Trend_Setter", "Moat", "Growth", "ETF"]:
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

        send_telegram_message(header + "\n".join(body_parts))
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
        send_telegram_message(msg)
        logger.warning("觸發 %d 個自訂價格警報。", len(triggered_msgs))


# ===========================================================================
# Scan History Service
# ===========================================================================


def get_scan_history(session: Session, ticker: str, limit: int = SCAN_HISTORY_DEFAULT_LIMIT) -> list[dict]:
    """取得指定股票的掃描歷史。"""
    ticker_upper = ticker.upper()
    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")

    logs = repo.find_scan_history(session, ticker_upper, limit)
    return [
        {
            "signal": log.signal,
            "market_status": log.market_status,
            "details": log.details,
            "scanned_at": log.scanned_at.isoformat() if log.scanned_at else None,
        }
        for log in logs
    ]


def get_latest_scan_logs(session: Session, limit: int = 50) -> list[dict]:
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
    ticker_upper = ticker.upper()
    stock = repo.find_stock_by_ticker(session, ticker_upper)
    if not stock:
        raise StockNotFoundError(f"找不到股票 {ticker_upper}。")

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
        send_telegram_message("📊 <b>Azusa Radar 每週摘要</b>\n\n目前無追蹤股票。")
        return {"message": "無追蹤股票。"}

    # 目前非 NORMAL 股票
    non_normal = [s for s in all_stocks if s.last_scan_signal != "NORMAL"]
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
        f"📊 <b>Azusa Radar 每週摘要</b>\n",
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
    send_telegram_message(message)
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
        return "Azusa Radar — 目前無追蹤股票。"

    non_normal = [s for s in stocks if s.last_scan_signal != "NORMAL"]
    health = round((len(stocks) - len(non_normal)) / len(stocks) * 100, 1)

    lines: list[str] = [f"Azusa Radar — Health: {health}%", ""]

    for cat in ["Trend_Setter", "Moat", "Growth", "ETF"]:
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
        category_str = item.get("category", "Growth")
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
                max_version = repo.get_max_thesis_version(session, ticker)
                thesis_log = ThesisLog(
                    stock_ticker=ticker,
                    content=thesis,
                    tags=tags_str,
                    version=max_version + 1,
                )
                repo.create_thesis_log(session, thesis_log)
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
