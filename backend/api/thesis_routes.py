"""
API — 觀點版控路由。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas import ThesisCreateRequest
from application.services import StockNotFoundError, add_thesis, get_thesis_history
from infrastructure.database import get_session

router = APIRouter()


@router.post("/ticker/{ticker}/thesis")
def create_thesis_route(
    ticker: str,
    payload: ThesisCreateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """為指定股票新增觀點。"""
    try:
        return add_thesis(session, ticker, payload.content, payload.tags)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ticker/{ticker}/thesis")
def get_thesis_history_route(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的觀點歷史。"""
    try:
        return get_thesis_history(session, ticker)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
