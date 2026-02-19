"""
Application — Portfolio Snapshot Service：每日快照的建立與查詢。
快照記錄每日投資組合總市值與各類別市值，供歷史績效圖表使用。
"""

import json as _json
from datetime import date, datetime, timezone

from sqlmodel import Session, select

from domain.entities import PortfolioSnapshot
from logging_config import get_logger

logger = get_logger(__name__)


def take_daily_snapshot(session: Session) -> PortfolioSnapshot:
    """
    計算當前投資組合市值並儲存今日快照（存在則更新，不存在則新增）。

    Args:
        session: SQLModel DB session

    Returns:
        儲存後的 PortfolioSnapshot 實例
    """
    # Lazy import to avoid circular dependency: snapshot_service ↔ rebalance_service
    from application.rebalance_service import calculate_rebalance

    rebalance = calculate_rebalance(session)
    total_value: float = rebalance.get("total_value", 0.0)
    display_currency: str = rebalance.get("display_currency", "USD")

    # Build {category: market_value} from categories dict
    categories: dict = rebalance.get("categories", {})
    category_values: dict[str, float] = {
        cat: info.get("market_value", 0.0) for cat, info in categories.items()
    }

    # Fetch S&P 500 close as benchmark
    benchmark_value: float | None = None
    try:
        from infrastructure.market_data import get_technical_signals

        sp500 = get_technical_signals("^GSPC")
        benchmark_value = sp500.get("price")
    except Exception as exc:
        logger.warning("無法取得 S&P 500 基準價格：%s", exc)

    today = datetime.now(timezone.utc).date()

    # Upsert: check for existing snapshot on today's date
    existing = session.exec(
        select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == today)
    ).first()

    if existing is not None:
        existing.total_value = total_value
        existing.category_values = _json.dumps(category_values)
        existing.display_currency = display_currency
        existing.benchmark_value = benchmark_value
        existing.created_at = datetime.now(timezone.utc)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info(
            "投資組合快照已更新：%s  total=%.2f %s",
            today,
            total_value,
            display_currency,
        )
        return existing

    snapshot = PortfolioSnapshot(
        snapshot_date=today,
        total_value=total_value,
        category_values=_json.dumps(category_values),
        display_currency=display_currency,
        benchmark_value=benchmark_value,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    logger.info(
        "投資組合快照已建立：%s  total=%.2f %s", today, total_value, display_currency
    )
    return snapshot


def get_snapshots(session: Session, days: int = 30) -> list[PortfolioSnapshot]:
    """
    取得最近 N 天的快照，依日期升冪排列（最舊在前）。

    Args:
        session: SQLModel DB session
        days: 回溯天數（預設 30）

    Returns:
        PortfolioSnapshot 列表
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    return list(
        session.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_date >= cutoff)
            .order_by(PortfolioSnapshot.snapshot_date)
        ).all()
    )


def get_snapshot_range(
    session: Session, start: date, end: date
) -> list[PortfolioSnapshot]:
    """
    取得指定日期區間的快照，依日期升冪排列。

    Args:
        session: SQLModel DB session
        start: 起始日期（含）
        end: 結束日期（含）

    Returns:
        PortfolioSnapshot 列表
    """
    return list(
        session.exec(
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.snapshot_date >= start,
                PortfolioSnapshot.snapshot_date <= end,
            )
            .order_by(PortfolioSnapshot.snapshot_date)
        ).all()
    )
