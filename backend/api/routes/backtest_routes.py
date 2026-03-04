"""
API — Signal backtesting routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session

from api.rate_limit import limiter
from api.schemas import BacktestDetailResponse, BacktestSummaryResponse
from application.services import get_backtest_detail, get_backtest_summary
from domain.analysis import SIGNAL_DIRECTION
from infrastructure.database import get_session

router = APIRouter()


@router.get(
    "/backtest/summary",
    response_model=BacktestSummaryResponse,
    summary="Get signal backtest summary",
)
@limiter.limit("30/minute")
def get_backtest_summary_route(
    request: Request,
    session: Session = Depends(get_session),
) -> BacktestSummaryResponse:
    data = get_backtest_summary(session)
    return BacktestSummaryResponse(**data)


@router.get(
    "/backtest/signal/{signal}",
    response_model=BacktestDetailResponse,
    summary="Get backtest detail for a signal",
)
@limiter.limit("30/minute")
def get_backtest_signal_detail_route(
    request: Request,
    signal: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> BacktestDetailResponse:
    signal_upper = signal.upper()
    if signal_upper not in SIGNAL_DIRECTION:
        raise HTTPException(status_code=404, detail=f"Unknown signal: {signal_upper}")

    data = get_backtest_detail(session, signal_upper, limit=limit)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No backtest data for signal: {signal_upper}",
        )
    return BacktestDetailResponse(**data)
