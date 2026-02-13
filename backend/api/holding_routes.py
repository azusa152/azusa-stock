"""
API — 持倉 (Holding) 管理與再平衡 (Rebalance) 路由。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.schemas import (
    CashHoldingRequest,
    CurrencyExposureResponse,
    FXAlertResponse,
    HoldingRequest,
    HoldingResponse,
    ImportResponse,
    MessageResponse,
    RebalanceResponse,
    WithdrawRequest,
    WithdrawResponse,
    XRayAlertResponse,
)
from application.services import (
    StockNotFoundError,
    calculate_currency_exposure,
    calculate_rebalance,
    calculate_withdrawal,
    send_fx_alerts,
    send_xray_warnings,
)
from domain.constants import DEFAULT_USER_ID, ERROR_HOLDING_NOT_FOUND
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


@router.get(
    "/holdings", response_model=list[HoldingResponse], summary="List all holdings"
)
def list_holdings(session: Session = Depends(get_session)) -> list[HoldingResponse]:
    """取得所有持倉。"""
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()
    return [_holding_to_response(h) for h in holdings]


@router.post("/holdings", response_model=HoldingResponse, summary="Add a holding")
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


@router.post(
    "/holdings/cash", response_model=HoldingResponse, summary="Add a cash holding"
)
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


@router.put(
    "/holdings/{holding_id}", response_model=HoldingResponse, summary="Update a holding"
)
def update_holding(
    holding_id: int,
    payload: HoldingRequest,
    session: Session = Depends(get_session),
) -> HoldingResponse:
    """更新持倉。"""
    holding = session.get(Holding, holding_id)
    if not holding:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_HOLDING_NOT_FOUND, "detail": "持倉不存在。"},
        )
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


@router.delete(
    "/holdings/{holding_id}", response_model=MessageResponse, summary="Delete a holding"
)
def delete_holding(
    holding_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """刪除持倉。"""
    holding = session.get(Holding, holding_id)
    if not holding:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_HOLDING_NOT_FOUND, "detail": "持倉不存在。"},
        )
    ticker = holding.ticker
    session.delete(holding)
    session.commit()
    logger.info("刪除持倉：%s", ticker)
    return {"message": f"持倉 {ticker} 已刪除。"}


# ---------------------------------------------------------------------------
# Holdings Import / Export
# ---------------------------------------------------------------------------


@router.get("/holdings/export", summary="Export all holdings as JSON")
def export_holdings(session: Session = Depends(get_session)) -> list[dict]:
    """匯出所有持倉（JSON 格式）。"""
    holdings = session.exec(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID)
    ).all()
    return [
        {
            "ticker": h.ticker,
            "category": h.category.value
            if hasattr(h.category, "value")
            else h.category,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "broker": h.broker,
            "currency": h.currency,
            "account_type": h.account_type,
            "is_cash": h.is_cash,
        }
        for h in holdings
    ]


@router.post(
    "/holdings/import",
    response_model=ImportResponse,
    summary="Bulk import holdings (replace)",
)
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


@router.get(
    "/rebalance",
    response_model=RebalanceResponse,
    summary="Calculate rebalance analysis",
)
def get_rebalance(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> RebalanceResponse:
    """計算再平衡分析（目標 vs 實際配置）。可透過 display_currency 指定顯示幣別。"""
    return calculate_rebalance(
        session, display_currency=display_currency.strip().upper()
    )


@router.post(
    "/rebalance/xray-alert",
    response_model=XRayAlertResponse,
    summary="Trigger X-Ray alert via Telegram",
)
def trigger_xray_alert(
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> dict:
    """觸發 X-Ray 穿透式持倉分析並發送 Telegram 警告。"""
    rebalance = calculate_rebalance(
        session, display_currency=display_currency.strip().upper()
    )
    xray = rebalance.get("xray", [])
    warnings = send_xray_warnings(xray, display_currency, session)
    return {
        "message": f"X-Ray 分析完成，{len(warnings)} 筆警告已發送。",
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Smart Withdrawal (聰明提款機)
# ---------------------------------------------------------------------------


@router.post(
    "/withdraw",
    response_model=WithdrawResponse,
    summary="Smart withdrawal plan (Liquidity Waterfall)",
)
def calculate_withdraw_route(
    payload: WithdrawRequest,
    session: Session = Depends(get_session),
) -> WithdrawResponse:
    """
    聰明提款：根據 Liquidity Waterfall 演算法產生賣出建議。
    優先順序：再平衡超配 → 節稅（虧損持倉）→ 流動性（Cash/Bond 優先）。
    """
    try:
        result = calculate_withdrawal(
            session,
            target_amount=payload.target_amount,
            display_currency=payload.display_currency.strip().upper(),
            notify=payload.notify,
        )
        return WithdrawResponse(**result)
    except StockNotFoundError as e:
        from domain.constants import ERROR_PROFILE_NOT_FOUND

        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": str(e)},
        )


# ---------------------------------------------------------------------------
# Currency Exposure Monitor
# ---------------------------------------------------------------------------


@router.get(
    "/currency-exposure",
    response_model=CurrencyExposureResponse,
    summary="Calculate currency exposure",
)
def get_currency_exposure(
    session: Session = Depends(get_session),
) -> CurrencyExposureResponse:
    """計算匯率曝險分析：幣別分佈、匯率變動、風險等級與建議。"""
    return calculate_currency_exposure(session)


@router.post(
    "/currency-exposure/alert",
    response_model=FXAlertResponse,
    summary="Trigger FX alert via Telegram",
)
def trigger_fx_alert(
    session: Session = Depends(get_session),
) -> dict:
    """檢查匯率曝險並發送 Telegram 警報。"""
    alerts = send_fx_alerts(session)
    return {
        "message": f"匯率曝險檢查完成，{len(alerts)} 筆警報已發送。",
        "alerts": alerts,
    }
