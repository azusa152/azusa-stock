"""
i18n — Internationalization module for frontend.
Provides translation function that reads language from Streamlit session state.
"""

import json
from pathlib import Path

import streamlit as st

# Load all locale files at module import time
_LOCALES_DIR = Path(__file__).parent / "locales"
_TRANSLATIONS: dict[str, dict] = {}

for locale_file in _LOCALES_DIR.glob("*.json"):
    lang_code = locale_file.stem
    try:
        with open(locale_file, encoding="utf-8") as f:
            _TRANSLATIONS[lang_code] = json.load(f)
    except Exception as e:
        st.error(f"Failed to load language pack: {lang_code} — {e}")


def t(key: str, **kwargs) -> str:
    """
    Translate a key using language from st.session_state['language'].

    Fallback chain: session language -> zh-TW -> raw key string

    Args:
        key: Dot-notation key (e.g., "nav.dashboard")
        **kwargs: Optional format arguments for string interpolation

    Returns:
        Translated string with interpolated values

    Examples:
        >>> t("radar.panel.add_stock")
        '➕ 新增追蹤'
        >>> t("common.save")
        '儲存'
    """
    # Get language from session state (default to Traditional Chinese)
    lang = st.session_state.get("language", "zh-TW")

    # Try requested language
    if lang in _TRANSLATIONS:
        value = _get_nested_value(_TRANSLATIONS[lang], key)
        if value:
            return _safe_format(value, **kwargs)

    # Fallback to Traditional Chinese
    if lang != "zh-TW" and "zh-TW" in _TRANSLATIONS:
        value = _get_nested_value(_TRANSLATIONS["zh-TW"], key)
        if value:
            return _safe_format(value, **kwargs)

    # Last resort: return the key itself
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


def _safe_format(template: str, **kwargs) -> str:
    """
    Safely format a template string with given kwargs.

    Falls back to raw template if formatting fails.
    """
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template
