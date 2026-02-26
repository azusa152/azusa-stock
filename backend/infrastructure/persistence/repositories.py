"""
Infrastructure — Repository Pattern。
集中管理所有資料庫查詢，讓 Service 層不直接接觸 ORM 語法。
"""

from datetime import UTC, datetime

from sqlmodel import Session, func, select

from domain.constants import (
    DEFAULT_USER_ID,
    LATEST_SCAN_LOGS_DEFAULT_LIMIT,
    SCAN_HISTORY_DEFAULT_LIMIT,
)
from domain.entities import (
    FXWatchConfig,
    Guru,
    GuruFiling,
    GuruHolding,
    Holding,
    PriceAlert,
    RemovalLog,
    ScanLog,
    Stock,
    SystemTemplate,
    ThesisLog,
    UserInvestmentProfile,
    UserPreferences,
    UserTelegramSettings,
)
from domain.enums import StockCategory

# ===========================================================================
# Stock Repository
# ===========================================================================


def find_stock_by_ticker(session: Session, ticker: str) -> Stock | None:
    """根據 ticker 查詢單一股票。"""
    return session.get(Stock, ticker)


def find_active_stocks(session: Session) -> list[Stock]:
    """查詢所有啟用中的股票（依 display_order 排序）。"""
    statement = (
        select(Stock)
        .where(Stock.is_active == True)  # noqa: E712
        .order_by(Stock.display_order, Stock.ticker)
    )
    return list(session.exec(statement).all())


def find_active_stocks_by_category(
    session: Session,
    category: StockCategory,
) -> list[Stock]:
    """查詢指定分類中所有啟用的股票（依 display_order 排序）。"""
    statement = (
        select(Stock)
        .where(
            Stock.is_active == True,  # noqa: E712
            Stock.category == category,
        )
        .order_by(Stock.display_order, Stock.ticker)
    )
    return list(session.exec(statement).all())


def find_inactive_stocks(session: Session) -> list[Stock]:
    """查詢所有已移除的股票。"""
    statement = select(Stock).where(Stock.is_active == False)  # noqa: E712
    return list(session.exec(statement).all())


def save_stock(session: Session, stock: Stock) -> Stock:
    """新增或更新股票。"""
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock


def update_stock(session: Session, stock: Stock) -> None:
    """更新股票（不做 refresh）。"""
    session.add(stock)


def bulk_update_display_order(session: Session, ordered_tickers: list[str]) -> None:
    """批次更新多檔股票的 display_order（單一 SELECT + 批次寫入）。"""
    if not ordered_tickers:
        return
    stocks = session.exec(select(Stock).where(Stock.ticker.in_(ordered_tickers))).all()
    stock_map = {s.ticker: s for s in stocks}
    for index, ticker in enumerate(ordered_tickers):
        s = stock_map.get(ticker)
        if s:
            s.display_order = index
    session.commit()


def bulk_update_scan_signals(
    session: Session,
    updates: dict[str, str],
    signal_since_updates: dict[str, datetime | None] | None = None,
) -> None:
    """批次更新多檔股票的 last_scan_signal 與 signal_since。"""
    if not updates:
        return
    stocks = session.exec(select(Stock).where(Stock.ticker.in_(updates.keys()))).all()
    for stock in stocks:
        stock.last_scan_signal = updates[stock.ticker]
        if signal_since_updates and stock.ticker in signal_since_updates:
            stock.signal_since = signal_since_updates[stock.ticker]
    session.commit()


def find_previous_distinct_signal(
    session: Session, ticker: str, current_signal: str
) -> tuple[str | None, datetime | None]:
    """
    在 ScanLog 中找到緊接在目前連續訊號之前的最後一個不同訊號及其時間。
    回傳 (previous_signal, changed_at)，若無則回傳 (None, None)。
    """
    logs = list(
        session.exec(
            select(ScanLog)
            .where(ScanLog.stock_ticker == ticker)
            .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
            .limit(100)
        ).all()
    )
    idx = 0
    while idx < len(logs) and logs[idx].signal == current_signal:
        idx += 1
    if idx < len(logs):
        return logs[idx].signal, logs[idx].scanned_at
    return None, None


def count_consecutive_scans(session: Session, ticker: str, signal: str) -> int:
    """計算目前訊號連續出現的掃描次數（從最新往回算）。"""
    logs = list(
        session.exec(
            select(ScanLog)
            .where(ScanLog.stock_ticker == ticker)
            .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
            .limit(50)
        ).all()
    )
    count = 0
    for log in logs:
        if log.signal == signal:
            count += 1
        else:
            break
    return max(count, 1)


def find_recent_scan_logs_for_tickers(
    session: Session, tickers: list[str], limit_per_ticker: int = 100
) -> dict[str, list[ScanLog]]:
    """
    一次批次取得多檔股票的最新 ScanLog（單一 SQL 查詢）。
    回傳 ticker → logs（時間降序）的對應表，供呼叫端自行計算統計值。
    使用 ROW_NUMBER 窗函數或 Python 端分組取 top-N。
    """
    if not tickers:
        return {}
    all_logs = list(
        session.exec(
            select(ScanLog)
            .where(ScanLog.stock_ticker.in_(tickers))  # type: ignore[union-attr]
            .order_by(
                ScanLog.stock_ticker,  # type: ignore[union-attr]
                ScanLog.scanned_at.desc(),  # type: ignore[union-attr]
            )
        ).all()
    )
    grouped: dict[str, list[ScanLog]] = {}
    for log in all_logs:
        bucket = grouped.setdefault(log.stock_ticker, [])
        if len(bucket) < limit_per_ticker:
            bucket.append(log)
    return grouped


# ===========================================================================
# ThesisLog Repository
# ===========================================================================


def get_max_thesis_version(session: Session, ticker: str) -> int:
    """取得指定股票目前最大的觀點版本號。"""
    statement = select(func.max(ThesisLog.version)).where(
        ThesisLog.stock_ticker == ticker
    )
    max_version = session.exec(statement).one()
    return max_version or 0


def create_thesis_log(session: Session, thesis: ThesisLog) -> None:
    """新增一筆觀點紀錄。"""
    session.add(thesis)


def find_thesis_history(session: Session, ticker: str) -> list[ThesisLog]:
    """取得指定股票的觀點歷史（版本降序）。"""
    statement = (
        select(ThesisLog)
        .where(ThesisLog.stock_ticker == ticker)
        .order_by(ThesisLog.version.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())


# ===========================================================================
# RemovalLog Repository
# ===========================================================================


def create_removal_log(session: Session, log: RemovalLog) -> None:
    """新增一筆移除紀錄。"""
    session.add(log)


def find_latest_removal(session: Session, ticker: str) -> RemovalLog | None:
    """取得指定股票的最新移除紀錄。"""
    statement = (
        select(RemovalLog)
        .where(RemovalLog.stock_ticker == ticker)
        .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
    )
    return session.exec(statement).first()


def find_latest_removals_batch(
    session: Session, tickers: list[str]
) -> dict[str, RemovalLog]:
    """
    批次取得多檔股票的最新移除紀錄（避免 N+1）。
    利用子查詢找出每檔股票最新的 removal log。
    """
    if not tickers:
        return {}

    # 子查詢：每檔股票的最大 created_at
    subq = (
        select(
            RemovalLog.stock_ticker,
            func.max(RemovalLog.created_at).label("max_created"),
        )
        .where(RemovalLog.stock_ticker.in_(tickers))  # type: ignore[union-attr]
        .group_by(RemovalLog.stock_ticker)
    ).subquery()

    # 主查詢：用 join 取回完整的 RemovalLog
    statement = select(RemovalLog).join(
        subq,
        (RemovalLog.stock_ticker == subq.c.stock_ticker)
        & (RemovalLog.created_at == subq.c.max_created),
    )
    results = session.exec(statement).all()
    return {r.stock_ticker: r for r in results}


def find_removal_history(session: Session, ticker: str) -> list[RemovalLog]:
    """取得指定股票的完整移除歷史（時間降序）。"""
    statement = (
        select(RemovalLog)
        .where(RemovalLog.stock_ticker == ticker)
        .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())


# ===========================================================================
# ScanLog Repository
# ===========================================================================


def create_scan_log(session: Session, log: ScanLog) -> None:
    """新增一筆掃描紀錄。"""
    session.add(log)


def find_scan_history(
    session: Session, ticker: str, limit: int = SCAN_HISTORY_DEFAULT_LIMIT
) -> list[ScanLog]:
    """取得指定股票的掃描歷史（時間降序）。"""
    statement = (
        select(ScanLog)
        .where(ScanLog.stock_ticker == ticker)
        .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
        .limit(limit)
    )
    return list(session.exec(statement).all())


def find_latest_scan_logs(
    session: Session, limit: int = LATEST_SCAN_LOGS_DEFAULT_LIMIT
) -> list[ScanLog]:
    """取得最近的掃描紀錄（跨股票，時間降序）。"""
    statement = (
        select(ScanLog)
        .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
        .limit(limit)
    )
    return list(session.exec(statement).all())


def find_scan_logs_since(session: Session, since: datetime) -> list[ScanLog]:
    """取得指定時間之後的所有掃描紀錄。"""
    statement = (
        select(ScanLog)
        .where(ScanLog.scanned_at >= since)  # type: ignore[operator]
        .order_by(ScanLog.scanned_at.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())


# ===========================================================================
# PriceAlert Repository
# ===========================================================================


def create_price_alert(session: Session, alert: PriceAlert) -> PriceAlert:
    """新增一筆價格警報。"""
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def find_active_alerts_for_stock(session: Session, ticker: str) -> list[PriceAlert]:
    """取得指定股票的所有啟用中警報。"""
    statement = select(PriceAlert).where(
        PriceAlert.stock_ticker == ticker,
        PriceAlert.is_active == True,  # noqa: E712
    )
    return list(session.exec(statement).all())


def find_all_alerts_for_stock(session: Session, ticker: str) -> list[PriceAlert]:
    """取得指定股票的所有警報（含已停用）。"""
    statement = select(PriceAlert).where(PriceAlert.stock_ticker == ticker)
    return list(session.exec(statement).all())


def find_all_active_alerts(session: Session) -> list[PriceAlert]:
    """取得所有啟用中的警報。"""
    statement = select(PriceAlert).where(PriceAlert.is_active == True)  # noqa: E712
    return list(session.exec(statement).all())


def find_price_alert_by_id(session: Session, alert_id: int) -> PriceAlert | None:
    """根據 ID 查詢單一警報。"""
    return session.get(PriceAlert, alert_id)


def delete_price_alert(session: Session, alert: PriceAlert) -> None:
    """刪除一筆價格警報。"""
    session.delete(alert)
    session.commit()


# ===========================================================================
# FX Watch Repository
# ===========================================================================


def create_fx_watch(session: Session, watch: FXWatchConfig) -> FXWatchConfig:
    """新增一筆外匯監控配置。"""
    session.add(watch)
    session.commit()
    session.refresh(watch)
    return watch


def find_fx_watch_by_id(session: Session, watch_id: int) -> FXWatchConfig | None:
    """根據 ID 查詢單一外匯監控配置。"""
    return session.get(FXWatchConfig, watch_id)


def find_active_fx_watches(
    session: Session, user_id: str | None = None
) -> list[FXWatchConfig]:
    """取得所有啟用中的外匯監控配置。"""
    statement = select(FXWatchConfig).where(FXWatchConfig.is_active == True)  # noqa: E712
    if user_id is not None:
        statement = statement.where(FXWatchConfig.user_id == user_id)
    return list(session.exec(statement).all())


def find_all_fx_watches(
    session: Session, user_id: str | None = None
) -> list[FXWatchConfig]:
    """取得所有外匯監控配置（含已停用）。"""
    statement = select(FXWatchConfig)
    if user_id is not None:
        statement = statement.where(FXWatchConfig.user_id == user_id)
    return list(session.exec(statement).all())


def update_fx_watch(session: Session, watch: FXWatchConfig) -> FXWatchConfig:
    """更新外匯監控配置（通用）。"""
    watch.updated_at = datetime.now(UTC)
    session.add(watch)
    session.commit()
    session.refresh(watch)
    return watch


def update_fx_watch_last_alerted(
    session: Session, watch_id: int, alerted_at: datetime
) -> None:
    """更新外匯監控配置的最後警報時間。"""
    watch = session.get(FXWatchConfig, watch_id)
    if watch:
        watch.last_alerted_at = alerted_at
        watch.updated_at = datetime.now(UTC)
        session.add(watch)
        session.commit()


def delete_fx_watch(session: Session, watch: FXWatchConfig) -> None:
    """刪除一筆外匯監控配置。"""
    session.delete(watch)
    session.commit()


# ===========================================================================
# Guru Repository
# ===========================================================================


def find_all_active_gurus(session: Session) -> list[Guru]:
    """查詢所有啟用中的大師（依 ID 排序）。"""
    statement = (
        select(Guru).where(Guru.is_active == True).order_by(Guru.id)  # noqa: E712
    )
    return list(session.exec(statement).all())


def find_guru_by_cik(session: Session, cik: str) -> Guru | None:
    """根據 CIK 查詢大師。"""
    statement = select(Guru).where(Guru.cik == cik)
    return session.exec(statement).first()


def find_guru_by_id(session: Session, guru_id: int) -> Guru | None:
    """根據 ID 查詢大師。"""
    return session.get(Guru, guru_id)


def save_guru(session: Session, guru: Guru) -> Guru:
    """新增大師（含 refresh）。"""
    session.add(guru)
    session.commit()
    session.refresh(guru)
    return guru


def update_guru(session: Session, guru: Guru) -> Guru:
    """更新大師（含 refresh）。"""
    session.add(guru)
    session.commit()
    session.refresh(guru)
    return guru


def deactivate_guru(session: Session, guru: Guru) -> None:
    """停用大師（軟刪除）。"""
    guru.is_active = False
    session.add(guru)
    session.commit()


# ===========================================================================
# GuruFiling Repository
# ===========================================================================


def find_latest_filing_by_guru(session: Session, guru_id: int) -> GuruFiling | None:
    """查詢指定大師最新的 13F 申報記錄（依 report_date 降序）。"""
    statement = (
        select(GuruFiling)
        .where(GuruFiling.guru_id == guru_id)
        .order_by(GuruFiling.report_date.desc())  # type: ignore[union-attr]
        .limit(1)
    )
    return session.exec(statement).first()


def find_filings_by_guru(
    session: Session, guru_id: int, limit: int = 8
) -> list[GuruFiling]:
    """查詢指定大師的歷史申報（依 report_date 降序）。"""
    statement = (
        select(GuruFiling)
        .where(GuruFiling.guru_id == guru_id)
        .order_by(GuruFiling.report_date.desc())  # type: ignore[union-attr]
        .limit(limit)
    )
    return list(session.exec(statement).all())


def find_filing_by_accession(
    session: Session, accession_number: str
) -> GuruFiling | None:
    """根據 accession number 查詢申報（用於冪等同步判斷）。"""
    statement = select(GuruFiling).where(
        GuruFiling.accession_number == accession_number
    )
    return session.exec(statement).first()


def save_filing(session: Session, filing: GuruFiling) -> GuruFiling:
    """新增 13F 申報記錄（含 refresh）。"""
    session.add(filing)
    session.commit()
    session.refresh(filing)
    return filing


# ===========================================================================
# GuruHolding Repository
# ===========================================================================


def find_holdings_by_filing(session: Session, filing_id: int) -> list[GuruHolding]:
    """查詢指定申報的所有持倉，依 weight_pct 降序排列。"""
    statement = (
        select(GuruHolding)
        .where(GuruHolding.filing_id == filing_id)
        .order_by(GuruHolding.weight_pct.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())


def find_holdings_by_guru_latest(session: Session, guru_id: int) -> list[GuruHolding]:
    """查詢指定大師最新申報的所有持倉（依 weight_pct 降序）。"""
    latest = find_latest_filing_by_guru(session, guru_id)
    if latest is None:
        return []
    return find_holdings_by_filing(session, latest.id)


def find_holdings_by_ticker_across_gurus(
    session: Session, ticker: str
) -> list[GuruHolding]:
    """
    查詢所有大師中持有指定股票的最新持倉記錄。
    僅回傳每位大師最新申報中的持倉（避免重複舊季數據）。
    """
    # 子查詢：每位大師最新 filing_id
    subq = (
        select(
            GuruFiling.guru_id,
            func.max(GuruFiling.report_date).label("max_report"),
        ).group_by(GuruFiling.guru_id)
    ).subquery()

    latest_filing_subq = (
        select(GuruFiling.id.label("filing_id")).join(
            subq,
            (GuruFiling.guru_id == subq.c.guru_id)
            & (GuruFiling.report_date == subq.c.max_report),
        )
    ).subquery()

    statement = select(GuruHolding).where(
        GuruHolding.ticker == ticker,
        GuruHolding.filing_id.in_(  # type: ignore[union-attr]
            select(latest_filing_subq.c.filing_id)
        ),
    )
    return list(session.exec(statement).all())


def save_holdings_batch(session: Session, holdings: list[GuruHolding]) -> None:
    """批次儲存持倉記錄（單次 commit）。"""
    for holding in holdings:
        session.add(holding)
    session.commit()


def _latest_filing_ids_subquery():
    """
    共用子查詢：回傳每位大師最新申報的 filing_id 集合。

    使用方式：
        latest_ids = _latest_filing_ids_subquery()
        stmt = select(GuruHolding).where(
            GuruHolding.filing_id.in_(select(latest_ids.c.filing_id))
        )
    """
    latest_date_subq = (
        select(
            GuruFiling.guru_id,
            func.max(GuruFiling.report_date).label("max_report"),
        ).group_by(GuruFiling.guru_id)
    ).subquery()

    return (
        select(GuruFiling.id.label("filing_id")).join(
            latest_date_subq,
            (GuruFiling.guru_id == latest_date_subq.c.guru_id)
            & (GuruFiling.report_date == latest_date_subq.c.max_report),
        )
    ).subquery()


def find_all_guru_summaries(session: Session) -> list[dict]:
    """
    查詢所有啟用中大師的最新申報摘要（含申報總筆數）。

    回傳 list of dict，每筆含：
        id, display_name, latest_report_date, latest_filing_date,
        total_value, holdings_count, filing_count,
        top5_concentration_pct, turnover_pct
    """
    from domain.enums import HoldingAction

    # 子查詢：每位大師最新申報日期
    latest_subq = (
        select(
            GuruFiling.guru_id,
            func.max(GuruFiling.report_date).label("max_report"),
        ).group_by(GuruFiling.guru_id)
    ).subquery()

    # 每位大師的申報數
    count_subq = (
        select(
            GuruFiling.guru_id,
            func.count(GuruFiling.id).label("filing_count"),
        ).group_by(GuruFiling.guru_id)
    ).subquery()

    # 取得最新申報記錄
    latest_filing_stmt = select(GuruFiling).join(
        latest_subq,
        (GuruFiling.guru_id == latest_subq.c.guru_id)
        & (GuruFiling.report_date == latest_subq.c.max_report),
    )
    latest_filings = {f.guru_id: f for f in session.exec(latest_filing_stmt).all()}

    # 取得申報數
    filing_counts = {
        row[0]: row[1]
        for row in session.exec(
            select(count_subq.c.guru_id, count_subq.c.filing_count)
        ).all()
    }

    gurus = session.exec(
        select(Guru).where(Guru.is_active == True).order_by(Guru.id)  # noqa: E712
    ).all()

    results = []
    for guru in gurus:
        filing = latest_filings.get(guru.id)

        top5_concentration_pct = None
        turnover_pct = None

        if filing:
            # Top-5 concentration: sum of top-5 weight_pct excluding SOLD_OUT
            top5 = session.exec(
                select(GuruHolding.weight_pct)
                .where(
                    GuruHolding.filing_id == filing.id,
                    GuruHolding.weight_pct.isnot(None),  # type: ignore[union-attr]
                    GuruHolding.action != HoldingAction.SOLD_OUT.value,
                )
                .order_by(GuruHolding.weight_pct.desc())
                .limit(5)
            ).all()
            if top5:
                top5_concentration_pct = round(sum(top5), 1)

            # Turnover: (new_positions + sold_out) / holdings_count * 100
            if filing.holdings_count > 0:
                action_counts = session.exec(
                    select(GuruHolding.action, func.count().label("cnt"))
                    .where(GuruHolding.filing_id == filing.id)
                    .group_by(GuruHolding.action)
                ).all()
                action_map = {a: c for a, c in action_counts}
                churned = action_map.get(
                    HoldingAction.NEW_POSITION.value, 0
                ) + action_map.get(HoldingAction.SOLD_OUT.value, 0)
                turnover_pct = round(churned / filing.holdings_count * 100, 1)

        results.append(
            {
                "id": guru.id,
                "display_name": guru.display_name,
                "latest_report_date": filing.report_date if filing else None,
                "latest_filing_date": filing.filing_date if filing else None,
                "total_value": filing.total_value if filing else None,
                "holdings_count": filing.holdings_count if filing else 0,
                "filing_count": filing_counts.get(guru.id, 0),
                "style": guru.style,
                "tier": guru.tier,
                "top5_concentration_pct": top5_concentration_pct,
                "turnover_pct": turnover_pct,
            }
        )
    return results


def find_holding_history_by_guru(
    session: Session, guru_id: int, quarters: int = 3
) -> list[dict]:
    """Return per-ticker holding snapshots across the last N filings for a guru.

    For each ticker ever held across those filings, returns a list of quarterly
    snapshots: {report_date, shares, value, weight_pct, action}.
    Sorted by the latest quarter's weight_pct DESC (most important positions first).
    """
    filings = find_filings_by_guru(session, guru_id, limit=quarters)
    if not filings:
        return []

    filing_ids = [f.id for f in filings]
    filing_date_map = {f.id: f.report_date for f in filings}

    holdings = session.exec(
        select(GuruHolding)
        .where(GuruHolding.filing_id.in_(filing_ids))  # type: ignore[union-attr]
        .order_by(GuruHolding.filing_id.desc(), GuruHolding.weight_pct.desc())  # type: ignore[union-attr]
    ).all()

    ticker_map: dict[str, dict] = {}
    for h in holdings:
        key = h.ticker or h.cusip
        if key not in ticker_map:
            ticker_map[key] = {
                "ticker": h.ticker,
                "company_name": h.company_name,
                "quarters": [],
                "_latest_weight": None,
            }
        ticker_map[key]["quarters"].append(
            {
                "report_date": filing_date_map[h.filing_id],
                "shares": h.shares,
                "value": h.value,
                "weight_pct": h.weight_pct,
                "action": h.action,
            }
        )

    result = []
    for item in ticker_map.values():
        qs = sorted(item["quarters"], key=lambda x: x["report_date"])
        shares_series = [q["shares"] for q in qs]
        item["trend"] = _compute_trend(shares_series)
        item["quarters"] = list(reversed(qs))
        item["_latest_weight"] = qs[-1]["weight_pct"] if qs else None
        result.append(item)

    result.sort(key=lambda x: x["_latest_weight"] or 0, reverse=True)
    for item in result:
        del item["_latest_weight"]

    return result


def _compute_trend(shares_series: list[float]) -> str:
    """Classify overall trend from oldest to newest share count."""
    if len(shares_series) < 2:
        return "stable"
    first, last = shares_series[0], shares_series[-1]
    if last == 0:
        return "exited"
    if first == 0:
        return "new"
    change_pct = (last - first) / first * 100
    if change_pct >= 10:
        return "increasing"
    if change_pct <= -10:
        return "decreasing"
    return "stable"


def find_notable_changes_all_gurus(session: Session) -> dict[str, list[dict]]:
    """
    查詢所有大師最新申報中的新建倉（NEW_POSITION）和清倉（SOLD_OUT）。

    僅包含擁有 >= 2 筆申報的大師（第一筆申報無法計算真實 diff，
    所有持倉皆為 NEW_POSITION 的冷啟動假陽性）。

    回傳 dict with keys "new_positions" and "sold_outs"，每筆含：
        ticker, company_name, guru_id, guru_display_name, value, weight_pct, change_pct
    """
    from domain.enums import HoldingAction

    latest_filing_ids_subq = _latest_filing_ids_subquery()

    # 只包含擁有 >= 2 筆申報的大師（排除冷啟動假陽性）
    multi_filing_gurus = (
        select(GuruFiling.guru_id)
        .group_by(GuruFiling.guru_id)
        .having(func.count(GuruFiling.id) >= 2)
    ).subquery()

    notable_stmt = (
        select(GuruHolding, Guru.display_name)
        .join(
            latest_filing_ids_subq,
            GuruHolding.filing_id == latest_filing_ids_subq.c.filing_id,
        )
        .join(Guru, GuruHolding.guru_id == Guru.id)
        .join(
            multi_filing_gurus,
            GuruHolding.guru_id == multi_filing_gurus.c.guru_id,
        )
        .where(
            GuruHolding.action.in_(  # type: ignore[union-attr]
                [HoldingAction.NEW_POSITION.value, HoldingAction.SOLD_OUT.value]
            )
        )
    )
    rows = session.exec(notable_stmt).all()

    new_positions = []
    sold_outs = []
    for holding, guru_display_name in rows:
        entry = {
            "ticker": holding.ticker,
            "company_name": holding.company_name,
            "guru_id": holding.guru_id,
            "guru_display_name": guru_display_name,
            "value": holding.value,
            "weight_pct": holding.weight_pct,
            "change_pct": holding.change_pct,
        }
        if holding.action == HoldingAction.NEW_POSITION.value:
            new_positions.append(entry)
        else:
            sold_outs.append(entry)

    return {"new_positions": new_positions, "sold_outs": sold_outs}


def find_consensus_stocks(session: Session) -> list[dict]:
    """Return tickers held by >1 active guru in their latest filings.

    Excludes SOLD_OUT positions. Returns enriched shape with per-guru
    action/weight detail, avg weight, sector, and company name.
    """
    from domain.enums import HoldingAction

    latest_ids = _latest_filing_ids_subquery()

    # Single query: all relevant holdings with guru display names
    stmt = (
        select(GuruHolding, Guru.display_name)
        .join(latest_ids, GuruHolding.filing_id == latest_ids.c.filing_id)
        .join(Guru, GuruHolding.guru_id == Guru.id)
        .where(
            GuruHolding.ticker.isnot(None),  # type: ignore[union-attr]
            GuruHolding.action != HoldingAction.SOLD_OUT.value,
        )
    )
    rows = session.exec(stmt).all()

    # Aggregate: ticker → {company_name, sector, guru_details, total_value}
    ticker_map: dict[str, dict] = {}
    for holding, guru_display_name in rows:
        t = holding.ticker
        if t not in ticker_map:
            ticker_map[t] = {
                "company_name": holding.company_name,
                "sector": holding.sector,
                "guru_details": [],
                "total_value": 0.0,
            }
        # Deduplicate by display_name (one guru may hold multiple CUSIPs for same ticker)
        if not any(
            g["display_name"] == guru_display_name
            for g in ticker_map[t]["guru_details"]
        ):
            ticker_map[t]["guru_details"].append(
                {
                    "display_name": guru_display_name,
                    "action": holding.action,
                    "weight_pct": holding.weight_pct,
                }
            )
        ticker_map[t]["total_value"] += holding.value

    result = []
    for t, d in ticker_map.items():
        guru_details = d["guru_details"]
        if len(guru_details) <= 1:
            continue
        weights = [g["weight_pct"] for g in guru_details if g["weight_pct"] is not None]
        avg_weight_pct = sum(weights) / len(weights) if weights else None
        result.append(
            {
                "ticker": t,
                "company_name": d["company_name"],
                "guru_count": len(guru_details),
                "gurus": guru_details,
                "total_value": d["total_value"],
                "avg_weight_pct": avg_weight_pct,
                "sector": d["sector"],
            }
        )

    result.sort(key=lambda x: (-x["guru_count"], -x["total_value"]))
    return result


def find_sector_breakdown(session: Session) -> list[dict]:
    """
    彙總所有大師最新申報中有 sector 資料的持倉，依板塊分組。

    回傳 list of dict（依 weight_pct 降序），每筆含：
        sector, total_value, holding_count, weight_pct
    """
    from domain.enums import HoldingAction

    latest_filing_ids_subq = _latest_filing_ids_subquery()

    holdings_stmt = (
        select(GuruHolding)
        .join(
            latest_filing_ids_subq,
            GuruHolding.filing_id == latest_filing_ids_subq.c.filing_id,
        )
        .where(
            GuruHolding.sector.isnot(None),  # type: ignore[union-attr]
            GuruHolding.action != HoldingAction.SOLD_OUT.value,
        )
    )
    holdings = session.exec(holdings_stmt).all()

    sector_map: dict[str, dict] = {}
    for h in holdings:
        s = h.sector
        if s not in sector_map:
            sector_map[s] = {"total_value": 0.0, "holding_count": 0}
        sector_map[s]["total_value"] += h.value
        sector_map[s]["holding_count"] += 1

    grand_total = sum(d["total_value"] for d in sector_map.values())

    result = []
    for sector, d in sector_map.items():
        weight_pct = (d["total_value"] / grand_total * 100) if grand_total > 0 else 0.0
        result.append(
            {
                "sector": sector,
                "total_value": d["total_value"],
                "holding_count": d["holding_count"],
                "weight_pct": round(weight_pct, 2),
            }
        )
    result.sort(key=lambda x: x["weight_pct"], reverse=True)
    return result


def find_activity_feed(session: Session, limit: int = 15) -> dict:
    """Aggregate holdings across all gurus' latest filings.

    Returns two ranked lists:
    - most_bought: tickers with the most NEW_POSITION / INCREASED actions
    - most_sold:   tickers with the most SOLD_OUT / DECREASED actions

    Each item: ticker, company_name, guru_count, gurus (display names), total_value.
    Sorted by guru_count DESC, then total_value DESC.
    Uses a single query + Python aggregation (same pattern as find_consensus_stocks).
    """
    from domain.enums import HoldingAction

    latest_ids = _latest_filing_ids_subquery()

    buy_actions = [HoldingAction.NEW_POSITION.value, HoldingAction.INCREASED.value]
    sell_actions = [HoldingAction.SOLD_OUT.value, HoldingAction.DECREASED.value]
    all_actions = buy_actions + sell_actions

    # Single query: fetch all relevant holdings with guru display names
    stmt = (
        select(GuruHolding, Guru.display_name)
        .join(
            latest_ids,
            GuruHolding.filing_id == latest_ids.c.filing_id,
        )
        .join(Guru, GuruHolding.guru_id == Guru.id)
        .where(
            GuruHolding.action.in_(all_actions),
            GuruHolding.ticker.isnot(None),  # type: ignore[union-attr]
        )
    )
    rows = session.exec(stmt).all()

    def _aggregate(actions: list[str]) -> list[dict]:
        # ticker → {company_name, gurus (deduped), total_value}
        ticker_map: dict[str, dict] = {}
        for holding, guru_display_name in rows:
            if holding.action not in actions:
                continue
            t = holding.ticker
            if t not in ticker_map:
                ticker_map[t] = {
                    "company_name": holding.company_name,
                    "gurus": [],
                    "total_value": 0.0,
                }
            if guru_display_name not in ticker_map[t]["gurus"]:
                ticker_map[t]["gurus"].append(guru_display_name)
            ticker_map[t]["total_value"] += holding.value

        result = [
            {
                "ticker": t,
                "company_name": d["company_name"],
                "guru_count": len(d["gurus"]),
                "gurus": d["gurus"],
                "total_value": d["total_value"],
            }
            for t, d in ticker_map.items()
        ]
        result.sort(key=lambda x: (-x["guru_count"], -x["total_value"]))
        return result[:limit]

    return {
        "most_bought": _aggregate(buy_actions),
        "most_sold": _aggregate(sell_actions),
    }


def find_grand_portfolio(session: Session) -> dict:
    """Aggregate holdings across all active gurus' latest filings.

    Groups by ticker in Python. Excludes SOLD_OUT positions.
    Returns items sorted by combined_weight_pct DESC.
    Uses a single query + Python aggregation (same pattern as find_activity_feed).
    """
    from domain.enums import HoldingAction

    latest_ids = _latest_filing_ids_subquery()

    # Single query: fetch all non-SOLD_OUT holdings with guru display names
    stmt = (
        select(GuruHolding, Guru.display_name)
        .join(
            latest_ids,
            GuruHolding.filing_id == latest_ids.c.filing_id,
        )
        .join(Guru, GuruHolding.guru_id == Guru.id)
        .where(
            GuruHolding.action != HoldingAction.SOLD_OUT.value,
            GuruHolding.ticker.isnot(None),  # type: ignore[union-attr]
        )
    )
    rows = session.exec(stmt).all()

    # ticker → {company_name, sector, gurus (deduped), total_value, weight_pct_sum,
    #           weight_pct_count, action_counts}
    ticker_map: dict[str, dict] = {}
    for holding, guru_display_name in rows:
        t = holding.ticker
        if t not in ticker_map:
            ticker_map[t] = {
                "company_name": holding.company_name,
                "sector": holding.sector,
                "gurus": [],
                "total_value": 0.0,
                "weight_pct_sum": 0.0,
                "weight_pct_count": 0,
                "action_counts": {},
            }
        if guru_display_name not in ticker_map[t]["gurus"]:
            ticker_map[t]["gurus"].append(guru_display_name)
        ticker_map[t]["total_value"] += holding.value or 0.0
        if holding.weight_pct is not None:
            ticker_map[t]["weight_pct_sum"] += holding.weight_pct
            ticker_map[t]["weight_pct_count"] += 1
        ac = ticker_map[t]["action_counts"]
        ac[holding.action] = ac.get(holding.action, 0) + 1

    grand_total = sum(d["total_value"] for d in ticker_map.values())

    items = []
    for t, d in ticker_map.items():
        combined_weight_pct = (
            d["total_value"] / grand_total * 100 if grand_total > 0 else 0
        )
        avg_weight_pct = (
            d["weight_pct_sum"] / d["weight_pct_count"]
            if d["weight_pct_count"] > 0
            else None
        )
        dominant_action = (
            max(d["action_counts"], key=d["action_counts"].get)
            if d["action_counts"]
            else HoldingAction.UNCHANGED.value
        )
        items.append(
            {
                "ticker": t,
                "company_name": d["company_name"],
                "sector": d["sector"],
                "guru_count": len(d["gurus"]),
                "gurus": d["gurus"],
                "total_value": d["total_value"],
                "avg_weight_pct": avg_weight_pct,
                "combined_weight_pct": round(combined_weight_pct, 3),
                "dominant_action": dominant_action,
            }
        )

    items.sort(key=lambda x: x["combined_weight_pct"], reverse=True)

    # Sector breakdown for the grand portfolio
    sector_map: dict[str, float] = {}
    for item in items:
        sector = item["sector"] or "Unknown"
        sector_map[sector] = sector_map.get(sector, 0) + item["total_value"]
    sector_breakdown = [
        {
            "sector": s,
            "total_value": v,
            "holding_count": sum(1 for i in items if (i["sector"] or "Unknown") == s),
            "weight_pct": round(v / grand_total * 100, 2) if grand_total > 0 else 0,
        }
        for s, v in sorted(sector_map.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "items": items,
        "total_value": grand_total,
        "unique_tickers": len(items),
        "sector_breakdown": sector_breakdown,
    }


# ===========================================================================
# Holding Repository
# ===========================================================================


def find_all_holdings(session: Session) -> list[Holding]:
    """查詢所有持倉（依 ID 排序）。"""
    return list(session.exec(select(Holding).order_by(Holding.id)).all())


def find_holding_by_id(session: Session, holding_id: int) -> Holding | None:
    """根據 ID 查詢單一持倉。"""
    return session.get(Holding, holding_id)


def save_holding(session: Session, holding: Holding) -> Holding:
    """新增或更新持倉（含 refresh）。"""
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


def delete_holding(session: Session, holding: Holding) -> None:
    """刪除一筆持倉。"""
    session.delete(holding)
    session.commit()


def delete_all_holdings(session: Session) -> int:
    """刪除所有持倉，回傳刪除筆數。"""
    holdings = find_all_holdings(session)
    count = len(holdings)
    for h in holdings:
        session.delete(h)
    session.commit()
    return count


# ===========================================================================
# UserPreferences Repository
# ===========================================================================


def find_user_preferences(
    session: Session, user_id: str = DEFAULT_USER_ID
) -> UserPreferences | None:
    """查詢使用者偏好設定。"""
    return session.get(UserPreferences, user_id)


def save_user_preferences(session: Session, prefs: UserPreferences) -> UserPreferences:
    """新增或更新使用者偏好設定（含 refresh）。"""
    session.add(prefs)
    session.commit()
    session.refresh(prefs)
    return prefs


# ===========================================================================
# UserTelegramSettings Repository
# ===========================================================================


def find_telegram_settings(
    session: Session, user_id: str = DEFAULT_USER_ID
) -> UserTelegramSettings | None:
    """查詢使用者 Telegram 通知設定。"""
    return session.get(UserTelegramSettings, user_id)


def save_telegram_settings(
    session: Session, settings: UserTelegramSettings
) -> UserTelegramSettings:
    """新增或更新 Telegram 通知設定（含 refresh）。"""
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


# ===========================================================================
# UserInvestmentProfile / SystemTemplate Repository
# ===========================================================================


def find_system_templates(session: Session) -> list[SystemTemplate]:
    """查詢所有系統範本。"""
    return list(session.exec(select(SystemTemplate)).all())


def find_active_profile(
    session: Session, user_id: str = DEFAULT_USER_ID
) -> UserInvestmentProfile | None:
    """查詢指定使用者目前啟用中的投資組合設定檔。"""
    stmt = select(UserInvestmentProfile).where(
        UserInvestmentProfile.user_id == user_id,
        UserInvestmentProfile.is_active == True,  # noqa: E712
    )
    return session.exec(stmt).first()


def find_profile_by_id(
    session: Session, profile_id: int
) -> UserInvestmentProfile | None:
    """根據 ID 查詢投資組合設定檔。"""
    return session.get(UserInvestmentProfile, profile_id)


def save_profile(
    session: Session, profile: UserInvestmentProfile
) -> UserInvestmentProfile:
    """新增或更新投資組合設定檔（含 refresh）。"""
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
