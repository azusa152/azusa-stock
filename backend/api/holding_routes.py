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
    HoldingImportItem,
    HoldingRequest,
    HoldingResponse,
    ImportResponse,
    MessageResponse,
    RebalanceResponse,
    StressTestResponse,
    WithdrawRequest,
    WithdrawResponse,
    XRayAlertResponse,
)
from application.services import (
    StockNotFoundError,
    calculate_currency_exposure,
    calculate_rebalance,
    calculate_stress_test,
    calculate_withdrawal,
    send_fx_alerts,
    send_xray_warnings,
)
from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_HOLDING_NOT_FOUND,
    ERROR_INVALID_INPUT,
    GENERIC_VALIDATION_ERROR,
)
from domain.entities import Holding
from i18n import get_user_language, t
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
            detail={
                "error_code": ERROR_HOLDING_NOT_FOUND,
                "detail": t("api.holding_not_found", lang=get_user_language(session)),
            },
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
            detail={
                "error_code": ERROR_HOLDING_NOT_FOUND,
                "detail": t("api.holding_not_found", lang=get_user_language(session)),
            },
        )
    ticker = holding.ticker
    session.delete(holding)
    session.commit()
    logger.info("刪除持倉：%s", ticker)
    return {
        "message": t(
            "api.holding_deleted", lang=get_user_language(session), ticker=ticker
        )
    }


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
    data: list[HoldingImportItem],
    session: Session = Depends(get_session),
) -> dict:
    """
    批次匯入持倉（清除舊資料後重新匯入）。

    限制：
    - 最多一次匯入 1000 筆
    - ticker 長度限制 20 字元
    - quantity 必須大於 0
    """
    if len(data) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=get_user_language(session)),
            },
        )

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
            item_dict = item.model_dump()
            holding = Holding(
                user_id=DEFAULT_USER_ID,
                ticker=item_dict["ticker"],
                category=item_dict["category"],
                quantity=item_dict["quantity"],
                cost_basis=item_dict.get("cost_basis"),
                broker=item_dict.get("broker"),
                currency=item_dict["currency"],
                account_type=item_dict.get("account_type"),
                is_cash=item_dict.get("is_cash", False),
            )
            session.add(holding)
            count += 1
        except Exception as e:
            logger.warning("持倉匯入第 %d 筆失敗：%s", i + 1, e)
            errors.append(
                t(
                    "api.import_item_failed",
                    lang=get_user_language(session),
                    index=i + 1,
                )
            )

    session.commit()
    logger.info("匯入持倉完成：%d 筆成功，%d 筆失敗。", count, len(errors))
    return {
        "message": t("api.import_done", lang=get_user_language(session), count=count),
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
    try:
        return calculate_rebalance(
            session, display_currency=display_currency.strip().upper()
        )
    except StockNotFoundError as e:
        from domain.constants import ERROR_PROFILE_NOT_FOUND

        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": str(e)},
        ) from e


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
    try:
        rebalance = calculate_rebalance(
            session, display_currency=display_currency.strip().upper()
        )
        xray = rebalance.get("xray", [])
        warnings = send_xray_warnings(xray, display_currency, session)
        return {
            "message": t(
                "api.xray_done", lang=get_user_language(session), count=len(warnings)
            ),
            "warnings": warnings,
        }
    except StockNotFoundError as e:
        from domain.constants import ERROR_PROFILE_NOT_FOUND

        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": str(e)},
        ) from e


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
        "message": t(
            "api.fx_alert_done", lang=get_user_language(session), count=len(alerts)
        ),
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# Stress Test
# ---------------------------------------------------------------------------


@router.get(
    "/stress-test",
    response_model=StressTestResponse,
    summary="Calculate portfolio stress test",
)
def get_stress_test(
    scenario_drop_pct: float = -20.0,
    display_currency: str = "USD",
    session: Session = Depends(get_session),
) -> StressTestResponse:
    """
    計算組合壓力測試：評估市場崩盤情境下的預期損失。

    Args:
        scenario_drop_pct: 市場崩盤情境 % (範圍: -50 到 0，預設 -20)
        display_currency: 顯示幣別（預設 USD）
        session: DB session (injected)

    Returns:
        StressTestResponse: 壓力測試結果（portfolio_beta, total_loss, pain_level, advice, breakdown）

    Raises:
        HTTPException 404: 當無任何持倉時
        HTTPException 422: 當 scenario_drop_pct 超出範圍時
    """
    # 驗證 scenario_drop_pct 範圍
    if not -50 <= scenario_drop_pct <= 0:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_SCENARIO_DROP",
                "detail": t(
                    "api.scenario_range_error", lang=get_user_language(session)
                ),
            },
        )

    try:
        result = calculate_stress_test(
            session,
            scenario_drop_pct=scenario_drop_pct,
            display_currency=display_currency.strip().upper(),
        )
        lang = get_user_language(session)
        # Translate i18n keys in pain_level, disclaimer, and advice
        result["pain_level"] = {
            **result["pain_level"],
            "label": t(result["pain_level"]["label"], lang=lang),
        }
        result["disclaimer"] = t(result["disclaimer"], lang=lang)
        result["advice"] = [t(advice_key, lang=lang) for advice_key in result["advice"]]
        return StressTestResponse(**result)
    except StockNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_HOLDING_NOT_FOUND, "detail": str(e)},
        )
