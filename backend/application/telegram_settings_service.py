"""
Application — Telegram Settings Service。
封裝 Telegram 通知設定的查詢、更新與測試邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

import os

from fastapi import HTTPException
from sqlmodel import Session

from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_TELEGRAM_NOT_CONFIGURED,
    ERROR_TELEGRAM_SEND_FAILED,
    GENERIC_TELEGRAM_ERROR,
)
from domain.entities import UserTelegramSettings
from i18n import t
from infrastructure import repositories as repo
from infrastructure.crypto import encrypt_token
from infrastructure.notification import send_telegram_message_dual
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _mask_token(token: str | None) -> str:
    """Mask a bot token, showing only first 3 and last 3 characters."""
    if not token:
        return ""
    if len(token) <= 8:
        return "***"
    return f"{token[:3]}***{token[-3:]}"


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def get_settings(session: Session) -> dict:
    """Return telegram settings with bot_token masked."""
    settings = repo.find_telegram_settings(session)
    if not settings:
        return {
            "telegram_chat_id": "",
            "custom_bot_token_masked": "",
            "use_custom_bot": False,
        }
    return {
        "telegram_chat_id": settings.telegram_chat_id,
        "custom_bot_token_masked": _mask_token(settings.custom_bot_token),
        "use_custom_bot": settings.use_custom_bot,
    }


def update_settings(session: Session, payload: dict) -> dict:
    """Update telegram settings. Encrypts custom_bot_token if provided."""
    # Encrypt token before storing (if provided)
    # Dev mode: store plaintext when FERNET_KEY unset
    encrypted_token = None
    if payload.get("custom_bot_token"):
        if os.getenv("FERNET_KEY"):
            encrypted_token = encrypt_token(payload["custom_bot_token"])
        else:
            logger.warning(
                "FERNET_KEY 未設定，Token 以明文儲存（開發模式）。生產環境請設定 FERNET_KEY。"
            )
            encrypted_token = payload["custom_bot_token"]

    settings = repo.find_telegram_settings(session)
    if settings:
        settings.telegram_chat_id = payload["telegram_chat_id"]
        if encrypted_token is not None:
            settings.custom_bot_token = encrypted_token
        settings.use_custom_bot = payload["use_custom_bot"]
    else:
        settings = UserTelegramSettings(
            user_id=DEFAULT_USER_ID,
            telegram_chat_id=payload["telegram_chat_id"],
            custom_bot_token=encrypted_token,
            use_custom_bot=payload["use_custom_bot"],
        )
        session.add(settings)

    session.commit()
    session.refresh(settings)
    logger.info(
        "Telegram 設定已更新（Token 已加密）：chat_id=%s, use_custom_bot=%s",
        settings.telegram_chat_id,
        settings.use_custom_bot,
    )
    return {
        "telegram_chat_id": settings.telegram_chat_id,
        "custom_bot_token_masked": _mask_token(settings.custom_bot_token),
        "use_custom_bot": settings.use_custom_bot,
    }


def send_test_message(session: Session, lang: str) -> dict:
    """Send a test Telegram message. Raises HTTPException on failure."""
    settings = repo.find_telegram_settings(session)
    if not settings or not settings.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_TELEGRAM_NOT_CONFIGURED,
                "detail": t("api.telegram_not_configured", lang=lang),
            },
        )

    test_text = t("api.telegram_test_msg", lang=lang)
    try:
        send_telegram_message_dual(test_text, session)
        logger.info("Telegram 測試訊息已發送。")
        return {"message": t("api.telegram_test_sent", lang=lang)}
    except Exception as e:
        logger.error("Telegram 測試訊息發送失敗：%s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": ERROR_TELEGRAM_SEND_FAILED,
                "detail": t(GENERIC_TELEGRAM_ERROR, lang=lang),
            },
        ) from e
