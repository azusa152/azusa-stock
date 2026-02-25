"""
API — 投資組合快照路由。
提供歷史快照查詢及手動觸發快照建立。
"""

import json
import threading
from datetime import UTC, date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session

from api.rate_limit import limiter
from api.schemas import AcceptedResponse, SnapshotResponse, TwrResponse
from application.portfolio.snapshot_service import (
    backfill_benchmark_values,
    get_snapshot_range,
    get_snapshots,
)
from domain.entities import PortfolioSnapshot
from infrastructure.database import engine, get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _to_response(snap: PortfolioSnapshot) -> SnapshotResponse:
    """Convert a PortfolioSnapshot entity to the public API response schema."""
    try:
        category_values = json.loads(snap.category_values)
    except (TypeError, ValueError):
        category_values = {}
    try:
        benchmark_values = json.loads(snap.benchmark_values)
    except (TypeError, ValueError):
        benchmark_values = {}
    return SnapshotResponse(
        snapshot_date=snap.snapshot_date.isoformat(),
        total_value=snap.total_value,
        category_values=category_values,
        display_currency=snap.display_currency,
        benchmark_value=snap.benchmark_value,
        benchmark_values=benchmark_values,
    )


def _run_snapshot_background() -> None:
    """在背景執行緒中建立快照（自建 DB Session）。"""
    try:
        from application.portfolio.snapshot_service import take_daily_snapshot

        with Session(engine) as session:
            take_daily_snapshot(session)
    except Exception as exc:
        logger.error("背景快照建立失敗：%s", exc, exc_info=True)


def _run_backfill_background() -> None:
    """在背景執行緒中回填基準指數歷史資料（自建 DB Session）。"""
    try:
        with Session(engine) as session:
            updated = backfill_benchmark_values(session)
            logger.info("基準指數回填完成：%d 件", updated)
    except Exception as exc:
        logger.error("基準指數回填失敗：%s", exc, exc_info=True)


@router.get(
    "/snapshots",
    response_model=list[SnapshotResponse],
    summary="Get historical portfolio snapshots",
)
def list_snapshots(
    days: int = Query(default=30, ge=1, le=730, description="回溯天數（1–730）"),
    start: date | None = Query(
        default=None, description="起始日期（YYYY-MM-DD，與 days 互斥）"
    ),
    end: date | None = Query(
        default=None, description="結束日期（YYYY-MM-DD，與 days 互斥）"
    ),
    session: Session = Depends(get_session),
) -> list[SnapshotResponse]:
    """
    取得歷史投資組合快照。

    - 預設回傳最近 30 天，可透過 `days` 調整（最多 730 天）。
    - 若提供 `start` / `end`，則改用日期區間查詢（優先）。
    - 結果依日期升冪排列（最舊在前）。
    """
    if start is not None or end is not None:
        if start is None or end is None:
            raise HTTPException(
                status_code=422,
                detail="start 與 end 必須同時提供",
            )
        if start > end:
            raise HTTPException(
                status_code=422,
                detail="start 不得晚於 end",
            )
        return [_to_response(s) for s in get_snapshot_range(session, start, end)]

    return [_to_response(s) for s in get_snapshots(session, days=days)]


@router.get(
    "/snapshots/twr",
    response_model=TwrResponse,
    summary="Compute time-weighted return for a date range",
)
def get_twr(
    start: date | None = Query(
        default=None, description="起始日期（預設：今年 1 月 1 日）"
    ),
    end: date | None = Query(default=None, description="結束日期（預設：今日）"),
    session: Session = Depends(get_session),
) -> TwrResponse:
    """
    計算指定日期範圍的時間加權報酬率（TWR）。

    - 預設計算今年 YTD（start = 1/1, end = 今日）。
    - 若無足夠快照，twr_pct 回傳 None。
    """
    from datetime import datetime

    from domain.analysis import compute_twr

    today = datetime.now(UTC).date()
    effective_start = start or date(today.year, 1, 1)
    effective_end = end or today

    if effective_start > effective_end:
        raise HTTPException(
            status_code=422,
            detail="start 不得晚於 end",
        )

    snaps = get_snapshot_range(session, effective_start, effective_end)
    snap_dicts = [
        {"snapshot_date": s.snapshot_date.isoformat(), "total_value": s.total_value}
        for s in snaps
    ]
    twr_pct = compute_twr(snap_dicts)

    return TwrResponse(
        twr_pct=twr_pct,
        start_date=snap_dicts[0]["snapshot_date"] if snap_dicts else None,
        end_date=snap_dicts[-1]["snapshot_date"] if snap_dicts else None,
        snapshot_count=len(snap_dicts),
    )


@router.post(
    "/snapshots/take",
    response_model=AcceptedResponse,
    summary="Trigger daily portfolio snapshot (background)",
)
@limiter.limit("10/minute")
async def take_snapshot(
    request: Request,
) -> AcceptedResponse:
    """
    觸發每日快照建立（非同步背景執行）。
    若今日已有快照，則更新（upsert 語意）。

    Rate limited: 10/minute。
    """
    logger.info("快照觸發請求已收到，啟動背景執行緒。")
    threading.Thread(target=_run_snapshot_background, daemon=True).start()
    return AcceptedResponse(message="snapshot triggered")


@router.post(
    "/snapshots/backfill-benchmarks",
    response_model=AcceptedResponse,
    summary="Backfill benchmark prices for historical snapshots (background)",
)
@limiter.limit("3/minute")
async def backfill_benchmarks(
    request: Request,
) -> AcceptedResponse:
    """
    既存の空の benchmark_values を持つスナップショットに対して、
    VT / ^N225 / ^TWII / ^GSPC の過去終値を yfinance から一括取得し補完する。

    背景執行緒で非同步実行。完了までに数秒〜数十秒かかる場合がある。
    Rate limited: 3/minute。
    """
    logger.info("基準指數回填請求已收到，啟動背景執行緒。")
    threading.Thread(target=_run_backfill_background, daemon=True).start()
    return AcceptedResponse(message="benchmark backfill triggered")
