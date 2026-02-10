"""
Infrastructure — 通知適配器 (Telegram Bot API)。
將通知邏輯從路由層抽離，日後可替換為其他通知管道。
"""

import os

import requests as http_requests

from domain.constants import TELEGRAM_API_URL, TELEGRAM_REQUEST_TIMEOUT
from logging_config import get_logger

logger = get_logger(__name__)


def send_telegram_message(text: str) -> None:
    """透過 Telegram Bot API 發送通知。Token 未設定時靜默跳過。"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id or token.startswith("your-"):
        logger.debug("Telegram Token 未設定，跳過發送通知。")
        return

    url = TELEGRAM_API_URL.format(token=token)
    try:
        http_requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=TELEGRAM_REQUEST_TIMEOUT,
        )
        logger.info("Telegram 通知已發送。")
    except Exception as e:
        logger.error("Telegram 通知發送失敗：%s", e)
