"""
API — 使用者偏好設定路由。
支援跨裝置同步隱私模式等偏好。
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import PreferencesRequest, PreferencesResponse
from application.settings import preferences_service
from i18n import get_user_language
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
    return PreferencesResponse(**preferences_service.get_preferences(session))


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
    lang = get_user_language(session)
    return PreferencesResponse(
        **preferences_service.update_preferences(session, payload.model_dump(), lang)
    )
