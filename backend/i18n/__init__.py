"""
i18n — Internationalization module for backend.
Provides translation function with fallback chain and string interpolation.
"""

import json
from pathlib import Path
from typing import Any

from sqlmodel import Session

from logging_config import get_logger

logger = get_logger(__name__)

# Load all locale files at module import time
_LOCALES_DIR = Path(__file__).parent / "locales"
_TRANSLATIONS: dict[str, dict] = {}

for locale_file in _LOCALES_DIR.glob("*.json"):
    lang_code = locale_file.stem
    try:
        with open(locale_file, encoding="utf-8") as f:
            _TRANSLATIONS[lang_code] = json.load(f)
        logger.info("已載入語言包：%s", lang_code)
    except Exception as e:
        logger.error("載入語言包失敗：%s — %s", lang_code, e)


def get_user_language(session: Session) -> str:
    """
    Get user's preferred language from database.
    
    Args:
        session: SQLModel database session
        
    Returns:
        Language code (e.g., "zh-TW", "en", "ja", "zh-CN")
    """
    from domain.constants import DEFAULT_LANGUAGE, DEFAULT_USER_ID
    from domain.entities import UserPreferences
    
    prefs = session.get(UserPreferences, DEFAULT_USER_ID)
    return prefs.language if prefs else DEFAULT_LANGUAGE


def t(key: str, lang: str = "zh-TW", **kwargs: Any) -> str:
    """
    Translate a key to the specified language with optional formatting.

    Fallback chain: requested lang -> zh-TW -> raw key string

    Args:
        key: Dot-notation key (e.g., "webhook.missing_ticker")
        lang: Language code (e.g., "en", "ja", "zh-CN", "zh-TW")
        **kwargs: Optional format arguments for string interpolation

    Returns:
        Translated string with interpolated values

    Examples:
        >>> t("stock.added", lang="en", ticker="AAPL")
        'Added AAPL to watchlist'
        >>> t("scan.alert_header", lang="ja")
        'Folio スキャン（差分通知）'
    """
    # Try requested language
    if lang in _TRANSLATIONS:
        value = _get_nested_value(_TRANSLATIONS[lang], key)
        if value:
            return _safe_format(value, **kwargs)

    # Fallback to Traditional Chinese
    if lang != "zh-TW" and "zh-TW" in _TRANSLATIONS:
        value = _get_nested_value(_TRANSLATIONS["zh-TW"], key)
        if value:
            logger.warning("翻譯鍵 '%s' 在 '%s' 中未找到，使用繁體中文後備", key, lang)
            return _safe_format(value, **kwargs)

    # Last resort: return the key itself
    logger.warning("翻譯鍵 '%s' 未找到（語言：%s），返回鍵本身", key, lang)
    return key


def _get_nested_value(data: dict, dot_key: str) -> str | None:
    """
    Retrieve nested dict value using dot notation.

    Args:
        data: Translation dict
        dot_key: "parent.child.key" notation

    Returns:
        String value or None if not found
    """
    keys = dot_key.split(".")
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current if isinstance(current, str) else None


def _safe_format(template: str, **kwargs: Any) -> str:
    """
    Safely format a template string with given kwargs.

    Falls back to raw template if formatting fails.
    """
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError) as e:
        logger.warning("字串格式化失敗：%s（模板：%s，參數：%s）", e, template, kwargs)
        return template
