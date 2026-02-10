"""
Infrastructure — Repository Pattern。
集中管理所有資料庫查詢，讓 Service 層不直接接觸 ORM 語法。
"""

from sqlmodel import Session, func, select

from domain.entities import RemovalLog, Stock, ThesisLog
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


def bulk_update_scan_signals(session: Session, updates: dict[str, str]) -> None:
    """批次更新多檔股票的 last_scan_signal。"""
    for ticker, signal in updates.items():
        stock = session.get(Stock, ticker)
        if stock:
            stock.last_scan_signal = signal
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


def find_removal_history(session: Session, ticker: str) -> list[RemovalLog]:
    """取得指定股票的完整移除歷史（時間降序）。"""
    statement = (
        select(RemovalLog)
        .where(RemovalLog.stock_ticker == ticker)
        .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
    )
    return list(session.exec(statement).all())
