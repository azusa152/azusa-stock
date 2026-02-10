"""
API — 持倉 (Holding) 管理與再平衡 (Rebalance) 路由。
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.schemas import (
    CashHoldingRequest,
    HoldingRequest,
    HoldingResponse,
    RebalanceResponse,
)
from application.services import calculate_rebalance
from domain.constants import DEFAULT_USER_ID
from domain.entities import Holding
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _holding_to_response(h: Holding) -> HoldingResponse:
    return HoldingResponse(
        id=h.id,  # type: ignore[arg-type]
        ticker=h.ticker,
        category=h.category,
        quantity=h.quantity,
        cost_basis=h.cost_basis,
        broker=h.broker,
        currency=h.currency,
        account_type=h.account_type,
        is_cash=h.is_cash,
        updated_at=h.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Holdings CRUD
# ---------------------------------------------------------------------------


@router.get("/holdings", response_model=list[HoldingResponse])
def list_holdings(session: Session = Depends(get_session)) -> list[HoldingResponse]:
    """取得所有持倉。"""
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()
    return [_holding_to_response(h) for h in holdings]


@router.post("/holdings", response_model=HoldingResponse)
def create_holding(
    payload: HoldingRequest,
    session: Session = Depends(get_session),
) -> HoldingResponse:
    """新增持倉。"""
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=payload.ticker.strip().upper(),
        category=payload.category,
        quantity=payload.quantity,
        cost_basis=payload.cost_basis,
        broker=payload.broker,
        currency=payload.currency.strip().upper(),
        account_type=payload.account_type,
        is_cash=payload.is_cash,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    logger.info("新增持倉：%s（%s）", holding.ticker, holding.category)
    return _holding_to_response(holding)


@router.post("/holdings/cash", response_model=HoldingResponse)
def create_cash_holding(
    payload: CashHoldingRequest,
    session: Session = Depends(get_session),
) -> HoldingResponse:
    """新增現金持倉（簡化入口）。"""
    from domain.enums import StockCategory

    currency_upper = payload.currency.strip().upper()
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=currency_upper,
        category=StockCategory.CASH,
        quantity=payload.amount,
        cost_basis=1.0,
        broker=payload.broker,
        currency=currency_upper,
        account_type=payload.account_type,
        is_cash=True,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    logger.info("新增現金持倉：%s %.2f", holding.ticker, holding.quantity)
    return _holding_to_response(holding)


@router.put("/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(
    holding_id: int,
    payload: HoldingRequest,
    session: Session = Depends(get_session),
) -> HoldingResponse:
    """更新持倉。"""
    holding = session.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="持倉不存在。")
    holding.ticker = payload.ticker.strip().upper()
    holding.category = payload.category
    holding.quantity = payload.quantity
    holding.cost_basis = payload.cost_basis
    holding.broker = payload.broker
    holding.currency = payload.currency.strip().upper()
    holding.account_type = payload.account_type
    holding.is_cash = payload.is_cash
    holding.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(holding)
    return _holding_to_response(holding)


@router.delete("/holdings/{holding_id}")
def delete_holding(
    holding_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """刪除持倉。"""
    holding = session.get(Holding, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="持倉不存在。")
    ticker = holding.ticker
    session.delete(holding)
    session.commit()
    logger.info("刪除持倉：%s", ticker)
    return {"message": f"持倉 {ticker} 已刪除。"}


# ---------------------------------------------------------------------------
# Holdings Import / Export
# ---------------------------------------------------------------------------


@router.get("/holdings/export")
def export_holdings(session: Session = Depends(get_session)) -> list[dict]:
    """匯出所有持倉（JSON 格式）。"""
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()
    return [
        {
            "ticker": h.ticker,
            "category": h.category.value if hasattr(h.category, "value") else h.category,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "broker": h.broker,
            "currency": h.currency,
            "account_type": h.account_type,
            "is_cash": h.is_cash,
        }
        for h in holdings
    ]


@router.post("/holdings/import")
def import_holdings(
    data: list[dict],
    session: Session = Depends(get_session),
) -> dict:
    """批次匯入持倉（清除舊資料後重新匯入）。"""
    # 清除既有持倉
    existing = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()
    for h in existing:
        session.delete(h)

    count = 0
    errors: list[str] = []
    for i, item in enumerate(data):
        try:
            holding = Holding(
                user_id=DEFAULT_USER_ID,
                ticker=item["ticker"].strip().upper(),
                category=item["category"],
                quantity=item["quantity"],
                cost_basis=item.get("cost_basis"),
                broker=item.get("broker"),
                currency=item.get("currency", "USD").strip().upper(),
                account_type=item.get("account_type"),
                is_cash=item.get("is_cash", False),
            )
            session.add(holding)
            count += 1
        except Exception as e:
            errors.append(f"第 {i + 1} 筆：{e}")

    session.commit()
    logger.info("匯入持倉完成：%d 筆成功，%d 筆失敗。", count, len(errors))
    return {
        "message": f"匯入完成：{count} 筆成功。",
        "imported": count,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Rebalance Analysis
# ---------------------------------------------------------------------------


@router.get("/rebalance", response_model=RebalanceResponse)
def get_rebalance(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> RebalanceResponse:
    """計算再平衡分析（目標 vs 實際配置）。可透過 display_currency 指定顯示幣別。"""
    return calculate_rebalance(session, display_currency=display_currency.strip().upper())
