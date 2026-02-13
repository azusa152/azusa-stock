"""
API — Telegram 通知設定路由。
支援使用者自訂 Bot Token（雙模式：系統預設 / 自訂 Bot）。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas import (
    MessageResponse,
    TelegramSettingsRequest,
    TelegramSettingsResponse,
)
from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_TELEGRAM_NOT_CONFIGURED,
    ERROR_TELEGRAM_SEND_FAILED,
)
from domain.entities import UserTelegramSettings
from infrastructure.database import get_session
from infrastructure.notification import send_telegram_message_dual
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def _mask_token(token: str | None) -> str:
    """遮蔽 Bot Token，僅顯示前 3 碼與末 3 碼。"""
    if not token:
        return ""
    if len(token) <= 8:
        return "***"
    return f"{token[:3]}***{token[-3:]}"


@router.get(
    "/settings/telegram",
    response_model=TelegramSettingsResponse,
    summary="Get Telegram settings",
)
def get_telegram_settings(
    session: Session = Depends(get_session),
) -> TelegramSettingsResponse:
    """取得目前的 Telegram 通知設定。"""
    settings = session.get(UserTelegramSettings, DEFAULT_USER_ID)
    if not settings:
        return TelegramSettingsResponse(
            telegram_chat_id="",
            custom_bot_token_masked="",
            use_custom_bot=False,
        )
    return TelegramSettingsResponse(
        telegram_chat_id=settings.telegram_chat_id,
        custom_bot_token_masked=_mask_token(settings.custom_bot_token),
        use_custom_bot=settings.use_custom_bot,
    )


@router.put(
    "/settings/telegram",
    response_model=TelegramSettingsResponse,
    summary="Update Telegram settings",
)
def update_telegram_settings(
    payload: TelegramSettingsRequest,
    session: Session = Depends(get_session),
) -> TelegramSettingsResponse:
    """更新 Telegram 通知設定。"""
    settings = session.get(UserTelegramSettings, DEFAULT_USER_ID)
    if settings:
        settings.telegram_chat_id = payload.telegram_chat_id
        if payload.custom_bot_token is not None:
            settings.custom_bot_token = payload.custom_bot_token
        settings.use_custom_bot = payload.use_custom_bot
    else:
        settings = UserTelegramSettings(
            user_id=DEFAULT_USER_ID,
            telegram_chat_id=payload.telegram_chat_id,
            custom_bot_token=payload.custom_bot_token,
            use_custom_bot=payload.use_custom_bot,
        )
        session.add(settings)

    session.commit()
    session.refresh(settings)
    logger.info(
        "Telegram 設定已更新：chat_id=%s, use_custom_bot=%s",
        settings.telegram_chat_id,
        settings.use_custom_bot,
    )
    return TelegramSettingsResponse(
        telegram_chat_id=settings.telegram_chat_id,
        custom_bot_token_masked=_mask_token(settings.custom_bot_token),
        use_custom_bot=settings.use_custom_bot,
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
    settings = session.get(UserTelegramSettings, DEFAULT_USER_ID)

    if not settings or not settings.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_TELEGRAM_NOT_CONFIGURED,
                "detail": "尚未設定 Telegram Chat ID，請先儲存設定。",
            },
        )

    test_text = "✅ <b>Folio 測試訊息</b>\n\n恭喜！你的 Telegram 通知設定正確運作。"
    try:
        send_telegram_message_dual(test_text, session)
        logger.info("Telegram 測試訊息已發送。")
        return {"message": "✅ 測試訊息已發送，請檢查 Telegram。"}
    except Exception as e:
        logger.error("Telegram 測試訊息發送失敗：%s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": ERROR_TELEGRAM_SEND_FAILED,
                "detail": f"發送失敗：{e}",
            },
        ) from e
