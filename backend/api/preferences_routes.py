"""
API — 使用者偏好設定路由。
支援跨裝置同步隱私模式等偏好。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas import PreferencesRequest, PreferencesResponse
from domain.constants import (
    DEFAULT_NOTIFICATION_PREFERENCES,
    DEFAULT_USER_ID,
    ERROR_PREFERENCES_UPDATE_FAILED,
    GENERIC_PREFERENCES_ERROR,
)
from domain.entities import UserPreferences
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/settings/preferences",
    response_model=PreferencesResponse,
    summary="Get user preferences",
)
def get_preferences(
    session: Session = Depends(get_session),
) -> PreferencesResponse:
    """取得目前的使用者偏好設定。"""
    prefs = session.get(UserPreferences, DEFAULT_USER_ID)
    if not prefs:
        return PreferencesResponse(
            privacy_mode=False,
            notification_preferences=DEFAULT_NOTIFICATION_PREFERENCES,
        )
    return PreferencesResponse(
        privacy_mode=prefs.privacy_mode,
        notification_preferences=prefs.get_notification_prefs(),
    )


@router.put(
    "/settings/preferences",
    response_model=PreferencesResponse,
    summary="Update user preferences",
)
def update_preferences(
    payload: PreferencesRequest,
    session: Session = Depends(get_session),
) -> PreferencesResponse:
    """更新使用者偏好設定（upsert）。"""
    try:
        prefs = session.get(UserPreferences, DEFAULT_USER_ID)
        if prefs:
            prefs.privacy_mode = payload.privacy_mode
            if payload.notification_preferences is not None:
                prefs.set_notification_prefs(payload.notification_preferences)
        else:
            prefs = UserPreferences(
                user_id=DEFAULT_USER_ID,
                privacy_mode=payload.privacy_mode,
            )
            if payload.notification_preferences is not None:
                prefs.set_notification_prefs(payload.notification_preferences)
            session.add(prefs)

        session.commit()
        session.refresh(prefs)
        logger.info("使用者偏好已更新：privacy_mode=%s", prefs.privacy_mode)
        return PreferencesResponse(
            privacy_mode=prefs.privacy_mode,
            notification_preferences=prefs.get_notification_prefs(),
        )
    except Exception as e:
        logger.error("使用者偏好更新失敗：%s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": ERROR_PREFERENCES_UPDATE_FAILED,
                "detail": GENERIC_PREFERENCES_ERROR,
            },
        ) from e
