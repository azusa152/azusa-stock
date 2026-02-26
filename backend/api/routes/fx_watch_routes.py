"""
API — FX Watch 外匯監控路由。
提供 CRUD 操作與定期監控觸發端點。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas import (
    FXTimingResultResponse,
    FXWatchAlertResponse,
    FXWatchCheckResponse,
    FXWatchCheckResultItem,
    FXWatchCreateRequest,
    FXWatchResponse,
    FXWatchUpdateRequest,
    MessageResponse,
)
from application.portfolio.fx_watch_service import (
    check_fx_watches,
    create_watch,
    get_all_watches,
    remove_watch,
    send_fx_watch_alerts,
    update_watch,
)
from domain.constants import DEFAULT_USER_ID
from domain.entities import FXWatchConfig
from i18n import get_user_language, t
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Mapping Helpers
# ---------------------------------------------------------------------------


def _to_watch_response(w: FXWatchConfig) -> FXWatchResponse:
    """Map FXWatchConfig entity to FXWatchResponse schema."""
    return FXWatchResponse(
        id=w.id,
        user_id=w.user_id,
        base_currency=w.base_currency,
        quote_currency=w.quote_currency,
        recent_high_days=w.recent_high_days,
        consecutive_increase_days=w.consecutive_increase_days,
        alert_on_recent_high=w.alert_on_recent_high,
        alert_on_consecutive_increase=w.alert_on_consecutive_increase,
        reminder_interval_hours=w.reminder_interval_hours,
        is_active=w.is_active,
        last_alerted_at=w.last_alerted_at.isoformat() if w.last_alerted_at else None,
        created_at=w.created_at.isoformat(),
        updated_at=w.updated_at.isoformat(),
    )


def _to_result_item(r: dict, lang: str) -> FXWatchCheckResultItem:
    """Map service result dict to FXWatchCheckResultItem schema.

    recommendation and reasoning are translated to the user's language using
    the scenario code and interpolation vars produced by the domain layer.
    Emoji prefixes (💡 / 📊) are stripped — they are Telegram-only decoration.
    """
    timing = r["result"]
    scenario = timing.scenario or "no_signal"
    vars_ = timing.scenario_vars or {}
    recommendation = t(f"fx_watch.rec_{scenario}", lang=lang, **vars_).removeprefix(
        "💡 "
    )
    reasoning = t(f"fx_watch.rea_{scenario}", lang=lang, **vars_).removeprefix("📊 ")
    return FXWatchCheckResultItem(
        watch_id=r["watch_id"],
        pair=r["pair"],
        result=FXTimingResultResponse(
            base_currency=timing.base_currency,
            quote_currency=timing.quote_currency,
            current_rate=timing.current_rate,
            is_recent_high=timing.is_recent_high,
            lookback_high=timing.lookback_high,
            lookback_days=timing.lookback_days,
            consecutive_increases=timing.consecutive_increases,
            consecutive_threshold=timing.consecutive_threshold,
            alert_on_recent_high=timing.alert_on_recent_high,
            alert_on_consecutive_increase=timing.alert_on_consecutive_increase,
            should_alert=timing.should_alert,
            scenario=scenario,
            scenario_vars=vars_,
            recommendation=recommendation,
            reasoning=reasoning,
        ),
    )


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/fx-watch",
    response_model=list[FXWatchResponse],
    summary="Get all FX watch configs",
)
def get_fx_watch_configs(
    active_only: bool = False,
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> list[FXWatchResponse]:
    """
    取得所有外匯監控配置。

    Query Parameters:
    - active_only: 是否僅取啟用中的配置（預設 False）
    - user_id: 使用者 ID（預設 DEFAULT_USER_ID）
    """
    watches = get_all_watches(session, user_id=user_id, active_only=active_only)
    return [_to_watch_response(w) for w in watches]


@router.post(
    "/fx-watch",
    response_model=FXWatchResponse,
    summary="Create FX watch config",
    status_code=201,
)
def create_fx_watch_config(
    req: FXWatchCreateRequest,
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> FXWatchResponse:
    """
    新增外匯監控配置。

    Request Body:
    - base_currency: 基礎貨幣（例如 USD）
    - quote_currency: 報價貨幣（例如 TWD）
    - recent_high_days: 回溯天數（預設 30）
    - consecutive_increase_days: 連續上漲天數門檻（預設 3）
    - alert_on_recent_high: 是否啟用近期高點警報（預設 True）
    - alert_on_consecutive_increase: 是否啟用連續上漲警報（預設 True）
    - reminder_interval_hours: 提醒間隔（預設 24）
    """
    watch = create_watch(
        session=session,
        base_currency=req.base_currency,
        quote_currency=req.quote_currency,
        recent_high_days=req.recent_high_days,
        consecutive_increase_days=req.consecutive_increase_days,
        alert_on_recent_high=req.alert_on_recent_high,
        alert_on_consecutive_increase=req.alert_on_consecutive_increase,
        reminder_interval_hours=req.reminder_interval_hours,
        user_id=user_id,
    )
    return _to_watch_response(watch)


@router.patch(
    "/fx-watch/{watch_id}",
    response_model=FXWatchResponse,
    summary="Update FX watch config",
)
def update_fx_watch_config(
    watch_id: int,
    req: FXWatchUpdateRequest,
    session: Session = Depends(get_session),
) -> FXWatchResponse:
    """
    更新外匯監控配置。

    Path Parameters:
    - watch_id: 配置 ID

    Request Body:
    - recent_high_days: 回溯天數（可選）
    - consecutive_increase_days: 連續上漲天數門檻（可選）
    - alert_on_recent_high: 是否啟用近期高點警報（可選）
    - alert_on_consecutive_increase: 是否啟用連續上漲警報（可選）
    - reminder_interval_hours: 提醒間隔（可選）
    - is_active: 是否啟用（可選）
    """
    watch = update_watch(
        session=session,
        watch_id=watch_id,
        recent_high_days=req.recent_high_days,
        consecutive_increase_days=req.consecutive_increase_days,
        alert_on_recent_high=req.alert_on_recent_high,
        alert_on_consecutive_increase=req.alert_on_consecutive_increase,
        reminder_interval_hours=req.reminder_interval_hours,
        is_active=req.is_active,
    )
    if not watch:
        raise HTTPException(
            status_code=404, detail=f"FX watch config with ID {watch_id} not found"
        )

    return _to_watch_response(watch)


@router.delete(
    "/fx-watch/{watch_id}",
    response_model=MessageResponse,
    summary="Delete FX watch config",
)
def delete_fx_watch_config(
    watch_id: int,
    session: Session = Depends(get_session),
) -> MessageResponse:
    """
    刪除外匯監控配置。

    Path Parameters:
    - watch_id: 配置 ID
    """
    success = remove_watch(session, watch_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"FX watch config with ID {watch_id} not found"
        )

    return MessageResponse(message=f"FX watch config {watch_id} deleted successfully")


# ---------------------------------------------------------------------------
# Analysis & Alert Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/fx-watch/check",
    response_model=FXWatchCheckResponse,
    summary="Check FX watches (no alert)",
)
def check_fx_watch_alerts(
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> FXWatchCheckResponse:
    """
    檢查所有啟用中的外匯監控配置，產出分析結果（不發送通知）。

    Query Parameters:
    - user_id: 使用者 ID（預設 DEFAULT_USER_ID）

    Returns:
    - total_watches: 啟用中的配置數量
    - results: 分析結果列表（含配置 ID、貨幣對、分析結果）
    """
    results = check_fx_watches(session, user_id=user_id)
    lang = get_user_language(session)
    return FXWatchCheckResponse(
        total_watches=len(results),
        results=[_to_result_item(r, lang) for r in results],
    )


@router.post(
    "/fx-watch/alert",
    response_model=FXWatchAlertResponse,
    summary="Check FX watches & send Telegram alert",
)
def send_fx_watch_alert(
    user_id: str = DEFAULT_USER_ID,
    session: Session = Depends(get_session),
) -> FXWatchAlertResponse:
    """
    檢查所有啟用中的外匯監控配置，發送 Telegram 警報（帶冷卻機制）。

    Query Parameters:
    - user_id: 使用者 ID（預設 DEFAULT_USER_ID）

    Returns:
    - total_watches: 啟用中的配置數量
    - triggered_alerts: 觸發警報的數量
    - sent_alerts: 實際發送的警報數量
    - alerts: 觸發警報的詳細資訊
    """
    result = send_fx_watch_alerts(session, user_id=user_id)
    lang = get_user_language(session)
    return FXWatchAlertResponse(
        total_watches=result["total_watches"],
        triggered_alerts=result["triggered_alerts"],
        sent_alerts=result["sent_alerts"],
        alerts=[_to_result_item(a, lang) for a in result["alerts"]],
    )
