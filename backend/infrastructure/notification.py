"""
Infrastructure — 通知適配器 (Telegram Bot API)。
支援雙模式：系統預設 Bot（env）或使用者自訂 Bot（DB）。
支援通知偏好：依使用者設定過濾特定類型的通知。
自訂 Bot Token 使用 Fernet 加密存儲於資料庫。
"""

import os

import requests as http_requests
from sqlmodel import Session

from domain.constants import DEFAULT_USER_ID, TELEGRAM_API_URL, TELEGRAM_REQUEST_TIMEOUT
from infrastructure.crypto import decrypt_token
from logging_config import get_logger

logger = get_logger(__name__)


def is_notification_enabled(session: Session, notification_type: str) -> bool:
    """檢查指定類型的通知是否已啟用（依使用者偏好）。

    Args:
        session: DB session.
        notification_type: 通知類型 key（如 'scan_alerts', 'price_alerts'）。

    Returns:
        True 表示應發送通知，False 表示使用者已停用此類通知。
    """
    from domain.entities import UserPreferences

    prefs = session.get(UserPreferences, DEFAULT_USER_ID)
    if not prefs:
        return True  # 無偏好設定時預設全部啟用
    return prefs.get_notification_prefs().get(notification_type, True)


def _send(token: str, chat_id: str, text: str) -> None:
    """低層發送：透過指定的 token / chat_id 發送 Telegram 訊息。"""
    url = TELEGRAM_API_URL.format(token=token)
    try:
        response = http_requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=TELEGRAM_REQUEST_TIMEOUT,
        )
        if response.ok:
            logger.info("Telegram 通知已發送。")
        else:
            try:
                body = response.json() if response.content else {}
            except ValueError:
                body = {}
            logger.error(
                "Telegram 通知失敗（HTTP %s）：%s",
                response.status_code,
                body.get("description", response.text),
            )
    except Exception as e:
        logger.error("Telegram 通知發送失敗：%s", e)


def _env_credentials() -> tuple[str, str]:
    """從環境變數取得系統預設 Bot 憑證。"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def send_telegram_message(text: str) -> None:
    """透過 Telegram Bot API 發送通知（使用環境變數憑證）。Token 未設定時靜默跳過。"""
    token, chat_id = _env_credentials()

    if not token or not chat_id or token.startswith("your-"):
        logger.debug("Telegram Token 未設定，跳過發送通知。")
        return

    _send(token, chat_id, text)


def send_telegram_message_dual(text: str, session: Session) -> None:
    """
    雙模式 Telegram 發送：
    1. 查詢 UserTelegramSettings（自訂 Bot 設定）
    2. 若 use_custom_bot=True 且 token / chat_id 有效 → 使用自訂 Bot（自動解密）
    3. 否則 → 回退至環境變數（系統預設 Bot）

    Note: custom_bot_token 使用 Fernet 加密存儲，此處自動解密後使用。
    """
    from domain.entities import UserTelegramSettings

    settings = session.get(UserTelegramSettings, DEFAULT_USER_ID)

    if (
        settings
        and settings.use_custom_bot
        and settings.custom_bot_token
        and settings.telegram_chat_id
    ):
        logger.info("使用自訂 Bot 發送 Telegram 通知。")
        # Decrypt token before use (stored encrypted in DB)
        decrypted_token = decrypt_token(settings.custom_bot_token)
        if decrypted_token:
            _send(decrypted_token, settings.telegram_chat_id, text)
            return
        logger.warning("自訂 Bot Token 解密失敗，回退至環境變數。")

    # 回退：使用環境變數
    send_telegram_message(text)
