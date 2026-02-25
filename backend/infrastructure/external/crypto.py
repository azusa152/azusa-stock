"""
Infrastructure — 加密工具（Fernet 對稱加密）。
用於加密敏感資料（如 Telegram Bot Token）存入資料庫。
"""

import os

from cryptography.fernet import Fernet, InvalidToken
from logging_config import get_logger

logger = get_logger(__name__)


def get_fernet_key() -> bytes:
    """
    取得 Fernet 加密金鑰（從環境變數）。

    Returns:
        Fernet key (bytes).

    Raises:
        ValueError: 若 FERNET_KEY 未設定或格式不正確。
    """
    key = os.getenv("FERNET_KEY")
    if not key:
        raise ValueError(
            "FERNET_KEY 環境變數未設定。請執行 `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` 生成金鑰。"
        )
    return key.encode()


def encrypt_token(plaintext: str) -> str:
    """
    使用 Fernet 加密 token。

    Args:
        plaintext: 明文 token（如 Telegram Bot Token）。

    Returns:
        Base64 編碼的加密字串。

    Raises:
        ValueError: 若 FERNET_KEY 未設定或無效。
    """
    if not plaintext:
        return ""

    try:
        key = get_fernet_key()
        f = Fernet(key)
        encrypted = f.encrypt(plaintext.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error("加密失敗：%s", e)
        raise


def decrypt_token(encrypted: str) -> str:
    """
    使用 Fernet 解密 token。

    Args:
        encrypted: Base64 編碼的加密字串。

    Returns:
        明文 token。如果解密失敗（如金鑰錯誤），回傳空字串並記錄錯誤。
    """
    if not encrypted:
        return ""

    try:
        key = get_fernet_key()
        f = Fernet(key)
        decrypted = f.decrypt(encrypted.encode())
        return decrypted.decode()
    except (InvalidToken, ValueError) as e:
        logger.error("解密失敗（金鑰錯誤或資料損壞）：%s", e)
        return ""
    except Exception as e:
        logger.error("解密失敗：%s", e)
        return ""


def is_encrypted(token: str) -> bool:
    """
    判斷 token 是否已加密（啟發式：Fernet 加密結果長度 > 100）。

    Args:
        token: 待檢查的 token。

    Returns:
        True 表示可能已加密，False 表示明文。

    Note:
        Fernet 加密後的 token 長度總是 > 100 字元。
        Telegram bot token 格式為 "123456:ABC-DEF..."，長度約 45-50 字元。
        因此長度檢查是可靠的區分方式，無需實際解密。
    """
    if not token:
        return False

    # Length heuristic is sufficient:
    # - Fernet tokens are always > 100 chars
    # - Telegram tokens are always < 100 chars (typically 45-50)
    return len(token) > 100
