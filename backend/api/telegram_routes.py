"""
API — Telegram 通知設定路由。
支援使用者自訂 Bot Token（雙模式：系統預設 / 自訂 Bot）。
自訂 Bot Token 使用 Fernet 加密存儲於資料庫。
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import (
    MessageResponse,
    TelegramSettingsRequest,
    TelegramSettingsResponse,
)
from application import telegram_settings_service
from i18n import get_user_language
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/settings/telegram",
    response_model=TelegramSettingsResponse,
    summary="Get Telegram settings",
)
def get_telegram_settings(
    session: Session = Depends(get_session),
) -> TelegramSettingsResponse:
    """取得目前的 Telegram 通知設定。"""
    return TelegramSettingsResponse(**telegram_settings_service.get_settings(session))


@router.put(
    "/settings/telegram",
    response_model=TelegramSettingsResponse,
    summary="Update Telegram settings",
)
def update_telegram_settings(
    payload: TelegramSettingsRequest,
    session: Session = Depends(get_session),
) -> TelegramSettingsResponse:
    """
    更新 Telegram 通知設定。

    Note: custom_bot_token 在存入資料庫前會自動加密（Fernet）。
    """
    return TelegramSettingsResponse(
        **telegram_settings_service.update_settings(session, payload.model_dump())
    )


@router.post(
    "/settings/telegram/test",
    response_model=MessageResponse,
    summary="Send a test Telegram message",
)
def test_telegram_message(
    session: Session = Depends(get_session),
) -> dict:
    """發送測試訊息以驗證 Telegram 設定是否正確。"""
    lang = get_user_language(session)
    return telegram_settings_service.send_test_message(session, lang)
