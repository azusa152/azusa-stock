# pyright: reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""
Application — Portfolio Snapshot Service：每日快照的建立與查詢。
快照記錄每日投資組合總市值與各類別市值，供歷史績效圖表使用。
"""

import json as _json
from datetime import UTC, date, datetime, timedelta

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
    from application.portfolio.rebalance_service import calculate_rebalance

    rebalance = calculate_rebalance(session)
    total_value: float = rebalance.get("total_value", 0.0)
    display_currency: str = rebalance.get("display_currency", "USD")

    # Build {category: market_value} from categories dict
    categories: dict = rebalance.get("categories", {})
    category_values: dict[str, float] = {
        cat: info.get("market_value", 0.0) for cat, info in categories.items()
    }

    # Fetch multiple benchmark index prices
    from infrastructure.market_data import get_technical_signals

    benchmark_tickers = ["^GSPC", "VT", "^N225", "^TWII"]
    benchmark_prices: dict[str, float | None] = {}
    for ticker in benchmark_tickers:
        try:
            data = get_technical_signals(ticker)
            benchmark_prices[ticker] = data.get("price") if data is not None else None
        except Exception as exc:
            logger.warning("無法取得基準指數 %s 價格：%s", ticker, exc)
            benchmark_prices[ticker] = None
    benchmark_value: float | None = benchmark_prices.get("^GSPC")

    today = datetime.now(UTC).date()

    # Upsert: check for existing snapshot on today's date
    existing = session.exec(
        select(PortfolioSnapshot).where(PortfolioSnapshot.snapshot_date == today)
    ).first()

    if existing is not None:
        existing.total_value = total_value
        existing.category_values = _json.dumps(category_values)
        existing.display_currency = display_currency
        existing.benchmark_value = benchmark_value
        existing.benchmark_values = _json.dumps(benchmark_prices)
        existing.created_at = datetime.now(UTC)
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
        benchmark_values=_json.dumps(benchmark_prices),
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    logger.info(
        "投資組合快照已建立：%s  total=%.2f %s", today, total_value, display_currency
    )
    return snapshot


def _needs_backfill(bv_json: str) -> bool:
    """判定 benchmark_values 是否需要補填（空 JSON 或含 null 值）。"""
    try:
        parsed = _json.loads(bv_json)
    except (TypeError, ValueError):
        return True
    if not parsed:
        return True
    return any(v is None for v in parsed.values())


def backfill_benchmark_values(session: Session) -> int:
    """
    針對 benchmark_values 為空（'{}'）或含 null 值的快照，
    使用基準指數的日期範圍收盤價歷史一次性補填。

    - 每支 ticker 僅一次 API 呼叫（共 4 次），不隨快照數量增加。
    - 市場休日自動回退至最近交易日收盤價（pandas asof）。
    - 同步更新 benchmark_value 向下相容欄位（^GSPC）。

    Returns:
        實際更新的快照數量（至少有一筆基準價格非 null 才計入）
    """
    import pandas as pd

    from infrastructure.market_data import get_benchmark_close_history

    benchmark_tickers = ["^GSPC", "VT", "^N225", "^TWII"]

    all_snapshots = list(
        session.exec(
            select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_date)
        ).all()
    )
    snapshots = [s for s in all_snapshots if _needs_backfill(s.benchmark_values)]
    if not snapshots:
        logger.info("無需補填基準指數資料。")
        return 0

    min_date = snapshots[0].snapshot_date
    max_date = snapshots[-1].snapshot_date
    logger.info(
        "基準指數補填開始：%d 筆，期間 %s ～ %s",
        len(snapshots),
        min_date,
        max_date,
    )

    price_history: dict[str, pd.Series | None] = {}
    for ticker in benchmark_tickers:
        series = get_benchmark_close_history(ticker, min_date, max_date)
        price_history[ticker] = series
        logger.info(
            "基準指數歷史取得 %s：%d 筆",
            ticker,
            len(series) if series is not None else 0,
        )

    updated = 0
    for snap in snapshots:
        snap_date = snap.snapshot_date
        prices: dict[str, float | None] = {}

        for ticker in benchmark_tickers:
            series = price_history.get(ticker)
            if series is None or len(series) == 0:
                prices[ticker] = None
                continue
            try:
                idx = pd.Timestamp(snap_date, tz="UTC")
                if series.index.tz is None:
                    series = series.tz_localize("UTC")
                close = series.asof(idx)
                prices[ticker] = float(close) if pd.notna(close) else None
            except Exception as exc:
                logger.warning(
                    "收盤價取得失敗 ticker=%s date=%s：%s", ticker, snap_date, exc
                )
                prices[ticker] = None

        has_any_price = any(v is not None for v in prices.values())
        if not has_any_price:
            continue

        snap.benchmark_values = _json.dumps(prices)
        if prices.get("^GSPC") is not None:
            snap.benchmark_value = prices["^GSPC"]
        session.add(snap)
        updated += 1

    session.commit()
    logger.info("基準指數補填完成：%d 筆更新", updated)
    return updated


def get_snapshots(session: Session, days: int = 30) -> list[PortfolioSnapshot]:
    """
    取得最近 N 天的快照，依日期升冪排列（最舊在前）。

    Args:
        session: SQLModel DB session
        days: 回溯天數（預設 30）

    Returns:
        PortfolioSnapshot 列表
    """

    cutoff = datetime.now(UTC).date() - timedelta(days=days)
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
