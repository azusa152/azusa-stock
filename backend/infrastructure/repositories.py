"""
Infrastructure — Repository Pattern。
集中管理所有資料庫查詢，讓 Service 層不直接接觸 ORM 語法。
"""

from datetime import datetime, timezone

from sqlmodel import Session, func, select

from domain.constants import LATEST_SCAN_LOGS_DEFAULT_LIMIT, SCAN_HISTORY_DEFAULT_LIMIT
from domain.entities import (
    FXWatchConfig,
    Guru,
    GuruFiling,
    GuruHolding,
    PriceAlert,
    RemovalLog,
    ScanLog,
    Stock,
    ThesisLog,
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


def bulk_update_scan_signals(session: Session, updates: dict[str, str]) -> None:
    """批次更新多檔股票的 last_scan_signal（單一 SELECT + 批次寫入）。"""
    if not updates:
        return
    stocks = session.exec(select(Stock).where(Stock.ticker.in_(updates.keys()))).all()
    for stock in stocks:
        stock.last_scan_signal = updates[stock.ticker]
    session.commit()


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
    watch.updated_at = datetime.now(timezone.utc)
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
        watch.updated_at = datetime.now(timezone.utc)
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
