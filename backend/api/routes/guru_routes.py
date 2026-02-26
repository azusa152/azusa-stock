"""
API — Smart Money (大師足跡) 路由。
薄控制器：僅負責解析請求、呼叫 Service、回傳回應。

Routes:
  GET    /gurus                    — List all active gurus
  POST   /gurus                    — Add custom guru
  DELETE /gurus/{guru_id}          — Deactivate a guru
  POST   /gurus/sync               — Trigger 13F sync for all gurus
  POST   /gurus/{guru_id}/sync     — Trigger 13F sync for one guru
  GET    /gurus/{guru_id}/filing   — Latest filing summary
  GET    /gurus/{guru_id}/holdings — All holdings with actions
  GET    /gurus/{guru_id}/top      — Top N holdings by weight
  GET    /gurus/{guru_id}/qoq      — Quarter-over-quarter holding history
  GET    /gurus/grand-portfolio    — Aggregated portfolio across all active gurus
  GET    /resonance                — Portfolio resonance overview
  GET    /resonance/great-minds    — Great Minds Think Alike list
  GET    /resonance/{ticker}       — Which gurus hold this ticker
  POST   /gurus/notify             — Trigger filing season notification
"""

import threading

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session

from api.rate_limit import limiter
from api.schemas import (
    ActivityFeed,
    ActivityFeedItem,
    ConsensusStockItem,
    DashboardResponse,
    FilingHistoryItem,
    FilingHistoryResponse,
    GrandPortfolioResponse,
    GreatMindsEntryResponse,
    GreatMindsResponse,
    GuruCreate,
    GuruFilingResponse,
    GuruHoldingResponse,
    GuruResponse,
    GuruStyleLiteral,
    GuruSummaryItem,
    QoQResponse,
    ResonanceEntryResponse,
    ResonanceResponse,
    ResonanceTickerResponse,
    SeasonHighlightItem,
    SeasonHighlights,
    SectorBreakdownItem,
    SyncAllResponse,
    SyncResponse,
)
from application.guru.guru_service import add_guru, list_gurus, remove_guru
from application.guru.resonance_service import (
    compute_portfolio_resonance,
    get_great_minds_list,
    get_resonance_for_ticker,
)
from application.messaging.notification_service import send_filing_season_digest
from application.stock.filing_service import (
    get_dashboard_summary,
    get_filing_summary,
    get_grand_portfolio,
    get_guru_filing_history,
    get_holding_changes,
    get_holding_qoq,
    sync_all_gurus,
    sync_guru_filing,
)
from application.stock.filing_service import (
    get_top_holdings as filing_get_top_holdings,
)
from domain.constants import GURU_HOLDING_CHANGES_DISPLAY_LIMIT, GURU_TOP_HOLDINGS_COUNT
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/gurus", tags=["smart-money"])
resonance_router = APIRouter(prefix="/resonance", tags=["smart-money"])

# Mutex: prevent concurrent 13F syncs from hammering EDGAR rate limits
_sync_lock = threading.Lock()


# ===========================================================================
# Guru CRUD
# ===========================================================================


@router.get(
    "",
    response_model=list[GuruResponse],
    summary="List all active gurus",
)
def get_gurus(session: Session = Depends(get_session)) -> list[GuruResponse]:
    """取得所有啟用中的大師清單（含 is_default 標記）。"""
    gurus = list_gurus(session)
    return [
        GuruResponse(
            id=g.id,
            name=g.name,
            cik=g.cik,
            display_name=g.display_name,
            is_active=g.is_active,
            is_default=g.is_default,
            style=g.style,
            tier=g.tier,
        )
        for g in gurus
    ]


@router.post(
    "",
    response_model=GuruResponse,
    status_code=201,
    summary="Add a custom guru by CIK",
)
def create_guru(
    body: GuruCreate,
    session: Session = Depends(get_session),
) -> GuruResponse:
    """新增自訂大師。若 CIK 已存在且為停用狀態則重新啟用。"""
    guru = add_guru(
        session,
        name=body.name,
        cik=body.cik,
        display_name=body.display_name,
        style=body.style,
        tier=body.tier,
    )
    return GuruResponse(
        id=guru.id,
        name=guru.name,
        cik=guru.cik,
        display_name=guru.display_name,
        is_active=guru.is_active,
        is_default=guru.is_default,
        style=guru.style,
        tier=guru.tier,
    )


@router.delete(
    "/{guru_id}",
    response_model=dict,
    summary="Deactivate a guru (soft delete)",
)
def delete_guru(
    guru_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """停用大師（軟刪除，保留歷史申報資料）。"""
    success = remove_guru(session, guru_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Guru {guru_id} not found")
    return {"message": f"Guru {guru_id} deactivated"}


# ===========================================================================
# 13F Sync
# ===========================================================================


@router.post(
    "/sync",
    response_model=SyncAllResponse,
    summary="Trigger 13F sync for all tracked gurus",
)
@limiter.limit("5/minute")
def sync_all(
    request: Request,
    session: Session = Depends(get_session),
) -> SyncAllResponse:
    """觸發所有啟用中大師的 13F 同步（同步執行，適合排程呼叫）。"""
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Sync already in progress")
    try:
        raw_results = sync_all_gurus(session)
    finally:
        _sync_lock.release()

    sync_results = []
    synced = skipped = errors = 0
    for r in raw_results:
        status = r.get("status", "error")
        if status == "synced":
            synced += 1
        elif status == "skipped":
            skipped += 1
        else:
            errors += 1
        sync_results.append(
            SyncResponse(
                status=status,
                guru_id=r.get("guru_id"),
                message=r.get("error", ""),
                new_positions=r.get("new_positions", 0),
                sold_out=r.get("sold_out", 0),
                increased=r.get("increased", 0),
                decreased=r.get("decreased", 0),
            )
        )

    return SyncAllResponse(
        synced=synced,
        skipped=skipped,
        errors=errors,
        results=sync_results,
    )


@router.post(
    "/{guru_id}/sync",
    response_model=SyncResponse,
    summary="Trigger 13F sync for one guru",
)
@limiter.limit("10/minute")
def sync_one(
    request: Request,
    guru_id: int,
    session: Session = Depends(get_session),
) -> SyncResponse:
    """觸發指定大師的 13F 同步。"""
    result = sync_guru_filing(session, guru_id)
    status = result.get("status", "error")
    if status == "error" and result.get("error") == "guru not found":
        raise HTTPException(status_code=404, detail=f"Guru {guru_id} not found")
    return SyncResponse(
        status=status,
        guru_id=result.get("guru_id"),
        message=result.get("error", ""),
        new_positions=result.get("new_positions", 0),
        sold_out=result.get("sold_out", 0),
        increased=result.get("increased", 0),
        decreased=result.get("decreased", 0),
    )


# ===========================================================================
# Grand Portfolio
# ===========================================================================


@router.get(
    "/grand-portfolio",
    response_model=GrandPortfolioResponse,
    summary="Aggregated portfolio across all active gurus' latest 13F filings",
)
def get_grand_portfolio_endpoint(
    style: GuruStyleLiteral | None = Query(
        default=None, description="Filter by guru style"
    ),
    session: Session = Depends(get_session),
) -> GrandPortfolioResponse:
    """跨所有啟用中大師的最新 13F 持倉聚合視圖。當提供 style 時，僅彙總該風格大師的持倉。"""
    data = get_grand_portfolio(session, style=style)
    return GrandPortfolioResponse(**data)


# ===========================================================================
# Filing & Holdings Data
# ===========================================================================


@router.get(
    "/{guru_id}/filing",
    response_model=GuruFilingResponse,
    summary="Latest 13F filing summary for a guru",
)
def get_filing(
    guru_id: int,
    session: Session = Depends(get_session),
) -> GuruFilingResponse:
    """取得指定大師最新申報摘要，含分類持倉（新建倉、清倉、加碼、減碼）。"""
    summary = get_filing_summary(session, guru_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"No filing data found for guru {guru_id}",
        )
    return GuruFilingResponse(
        guru_id=guru_id,
        guru_display_name=summary.get("guru_display_name", ""),
        report_date=summary.get("report_date"),
        filing_date=summary.get("filing_date"),
        total_value=summary.get("total_value"),
        holdings_count=summary.get("holdings_count", 0),
        filing_url=summary.get("filing_url", ""),
        new_positions=summary.get("new_positions", 0),
        sold_out=summary.get("sold_out", 0),
        increased=summary.get("increased", 0),
        decreased=summary.get("decreased", 0),
        top_holdings=summary.get("top_holdings", []),
    )


@router.get(
    "/{guru_id}/holdings",
    response_model=list[GuruHoldingResponse],
    summary="Holding changes for a guru (action != UNCHANGED), sorted by significance",
)
def get_holdings(
    guru_id: int,
    limit: int = Query(
        default=GURU_HOLDING_CHANGES_DISPLAY_LIMIT,
        ge=1,
        le=200,
        description="Max number of changes to return (sorted by abs(change_pct) then weight_pct)",
    ),
    include_performance: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> list[GuruHoldingResponse]:
    """
    取得指定大師最新申報中有動作的持倉（排除 UNCHANGED）。

    結果依變動幅度 abs(change_pct) 降序排列，再依 weight_pct 降序，最多回傳 limit 筆。
    """
    changes = get_holding_changes(
        session, guru_id, limit=limit, include_performance=include_performance
    )
    return [
        GuruHoldingResponse(
            guru_id=guru_id,
            cusip=h.get("cusip", ""),
            ticker=h.get("ticker"),
            company_name=h.get("company_name", ""),
            value=h.get("value", 0.0),
            shares=h.get("shares", 0.0),
            action=h.get("action", "UNCHANGED"),
            change_pct=h.get("change_pct"),
            weight_pct=h.get("weight_pct"),
            report_date=h.get("report_date"),
            filing_date=h.get("filing_date"),
            price_change_pct=h.get("price_change_pct"),
        )
        for h in changes
    ]


@router.get(
    "/{guru_id}/top",
    response_model=list[GuruHoldingResponse],
    summary="Top N holdings by weight for a guru",
)
def get_top_holdings(
    guru_id: int,
    n: int = Query(
        default=GURU_TOP_HOLDINGS_COUNT, ge=1, le=50, description="Top N holdings"
    ),
    include_performance: bool = Query(default=False),
    session: Session = Depends(get_session),
) -> list[GuruHoldingResponse]:
    """取得指定大師持倉權重最高的前 N 支股票（預設 Top 10，最多 50）。"""
    top = filing_get_top_holdings(
        session, guru_id, n, include_performance=include_performance
    )
    if not top:
        raise HTTPException(
            status_code=404,
            detail=f"No filing data found for guru {guru_id}",
        )
    return [
        GuruHoldingResponse(
            guru_id=guru_id,
            cusip=h.get("cusip", ""),
            ticker=h.get("ticker"),
            company_name=h.get("company_name", ""),
            value=h.get("value", 0.0),
            shares=h.get("shares", 0.0),
            action=h.get("action", "UNCHANGED"),
            change_pct=h.get("change_pct"),
            weight_pct=h.get("weight_pct"),
            report_date=h.get("report_date"),
            filing_date=h.get("filing_date"),
            price_change_pct=h.get("price_change_pct"),
        )
        for h in top
    ]


@router.get(
    "/{guru_id}/qoq",
    response_model=QoQResponse,
    summary="Quarter-over-quarter holding history for a guru",
)
def get_guru_qoq(
    guru_id: int,
    quarters: int = Query(default=3, ge=2, le=8),
    session: Session = Depends(get_session),
) -> QoQResponse:
    """取得指定大師跨季度持倉歷史（預設最近 3 季）。"""
    data = get_holding_qoq(session, guru_id, quarters=quarters)
    return QoQResponse(**data)


# ===========================================================================
# Dashboard Aggregation
# ===========================================================================


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Aggregated dashboard summary across all gurus",
)
def get_dashboard(
    style: GuruStyleLiteral | None = Query(
        default=None, description="Filter by guru style"
    ),
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """
    取得跨大師的聚合儀表板摘要，供 Smart Money 總覽頁面使用。
    當提供 style 時，僅彙總符合該投資風格的大師資料。

    回傳：
    - gurus: 每位啟用中大師的最新申報摘要（含申報總筆數）
    - season_highlights: 本季新建倉與清倉列表
    - consensus: 被多位大師同時持有的共識股票列表
    - sector_breakdown: 依行業板塊彙總的持倉分佈

    ⚠️ 基於 13F 申報快照，非即時資料。
    """
    data = get_dashboard_summary(session, style=style)

    gurus = [GuruSummaryItem(**g) for g in data["gurus"]]

    highlights_raw = data["season_highlights"]
    season_highlights = SeasonHighlights(
        new_positions=[
            SeasonHighlightItem(**h) for h in highlights_raw["new_positions"]
        ],
        sold_outs=[SeasonHighlightItem(**h) for h in highlights_raw["sold_outs"]],
    )

    consensus = [ConsensusStockItem(**c) for c in data["consensus"]]
    sector_breakdown = [SectorBreakdownItem(**s) for s in data["sector_breakdown"]]

    feed_raw = data["activity_feed"]
    activity_feed = ActivityFeed(
        most_bought=[ActivityFeedItem(**i) for i in feed_raw["most_bought"]],
        most_sold=[ActivityFeedItem(**i) for i in feed_raw["most_sold"]],
    )

    return DashboardResponse(
        gurus=gurus,
        season_highlights=season_highlights,
        consensus=consensus,
        sector_breakdown=sector_breakdown,
        activity_feed=activity_feed,
    )


@router.get(
    "/{guru_id}/filings",
    response_model=FilingHistoryResponse,
    summary="Historical 13F filings list for a guru",
)
def get_filing_history(
    guru_id: int,
    session: Session = Depends(get_session),
) -> FilingHistoryResponse:
    """
    取得指定大師所有已同步申報的歷史列表（依 report_date 降序）。
    供 Smart Money 頁面時間軸顯示使用。
    """
    filings = get_guru_filing_history(session, guru_id)
    return FilingHistoryResponse(
        filings=[FilingHistoryItem(**f) for f in filings],
    )


# ===========================================================================
# Notifications
# ===========================================================================


@router.post(
    "/notify",
    response_model=dict,
    summary="Trigger filing season digest notification",
)
@limiter.limit("5/minute")
def trigger_filing_notification(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """發送本季所有大師 13F 申報摘要的 Telegram 通知。"""
    result = send_filing_season_digest(session)
    return result


# ===========================================================================
# Resonance Routes
# ===========================================================================


@resonance_router.get(
    "",
    response_model=ResonanceResponse,
    summary="Portfolio resonance overview (all gurus vs user watchlist/holdings)",
)
def get_resonance(
    session: Session = Depends(get_session),
) -> ResonanceResponse:
    """
    計算所有大師最新持倉與使用者關注清單／實際持倉的交集。

    回傳每位大師的重疊股票清單，依重疊數量降序排列。
    ⚠️ 基於 13F 申報快照，非即時資料。
    """
    results = compute_portfolio_resonance(session)
    entries = [
        ResonanceEntryResponse(
            guru_id=r["guru_id"],
            guru_display_name=r["guru_display_name"],
            overlapping_tickers=r["overlapping_tickers"],
            overlap_count=r["overlap_count"],
            holdings=r["holdings"],
        )
        for r in results
    ]
    return ResonanceResponse(
        results=entries,
        total_gurus=len(entries),
        gurus_with_overlap=sum(1 for e in entries if e.overlap_count > 0),
    )


@resonance_router.get(
    "/great-minds",
    response_model=GreatMindsResponse,
    summary='"Great Minds Think Alike" — stocks held by both user and gurus',
)
def get_great_minds(
    session: Session = Depends(get_session),
) -> GreatMindsResponse:
    """
    英雄所見略同：使用者（關注清單或持倉）＋至少一位大師同時持有的股票。

    按持有該股票的大師數量降序排列。
    ⚠️ 基於 13F 申報快照，非即時資料。
    """
    great_minds = get_great_minds_list(session)
    stocks = [
        GreatMindsEntryResponse(
            ticker=item["ticker"],
            guru_count=item["guru_count"],
            gurus=item["gurus"],
        )
        for item in great_minds
    ]
    return GreatMindsResponse(stocks=stocks, total_count=len(stocks))


@resonance_router.get(
    "/{ticker}",
    response_model=ResonanceTickerResponse,
    summary="Which gurus hold a specific ticker",
)
def get_resonance_ticker(
    ticker: str,
    session: Session = Depends(get_session),
) -> ResonanceTickerResponse:
    """
    查詢哪些大師的最新申報中持有指定股票（Radar 頁面徽章用）。

    ⚠️ 基於 13F 申報快照，非即時資料。
    """
    ticker = ticker.upper()
    gurus = get_resonance_for_ticker(session, ticker)
    return ResonanceTickerResponse(
        ticker=ticker,
        gurus=gurus,
        guru_count=len(gurus),
    )
