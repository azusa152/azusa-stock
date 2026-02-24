"""
Application — Preferences Service。
封裝使用者偏好設定的查詢與更新邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session

from domain.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_NOTIFICATION_PREFERENCES,
    DEFAULT_USER_ID,
    ERROR_PREFERENCES_UPDATE_FAILED,
    GENERIC_PREFERENCES_ERROR,
)
from domain.entities import UserPreferences
from i18n import t
from infrastructure import repositories as repo
from logging_config import get_logger

logger = get_logger(__name__)


def get_preferences(session: Session) -> dict:
    """Return user preferences, using defaults if not found."""
    prefs = repo.find_user_preferences(session)
    if not prefs:
        return {
            "language": DEFAULT_LANGUAGE,
            "privacy_mode": False,
            "notification_preferences": DEFAULT_NOTIFICATION_PREFERENCES,
        }
    return {
        "language": prefs.language,
        "privacy_mode": prefs.privacy_mode,
        "notification_preferences": prefs.get_notification_prefs(),
    }


def update_preferences(session: Session, payload: dict, lang: str) -> dict:
    """Update user preferences (upsert). Raises HTTPException on failure."""
    try:
        prefs = repo.find_user_preferences(session)
        if prefs:
            if payload.get("language") is not None:
                prefs.language = payload["language"]
            prefs.privacy_mode = payload["privacy_mode"]
            if payload.get("notification_preferences") is not None:
                prefs.set_notification_prefs(payload["notification_preferences"])
        else:
            prefs = UserPreferences(
                user_id=DEFAULT_USER_ID,
                language=payload.get("language") or DEFAULT_LANGUAGE,
                privacy_mode=payload["privacy_mode"],
            )
            if payload.get("notification_preferences") is not None:
                prefs.set_notification_prefs(payload["notification_preferences"])
            session.add(prefs)

        session.commit()
        session.refresh(prefs)
        logger.info(
            "使用者偏好已更新：language=%s, privacy_mode=%s",
            prefs.language,
            prefs.privacy_mode,
        )
        return {
            "language": prefs.language,
            "privacy_mode": prefs.privacy_mode,
            "notification_preferences": prefs.get_notification_prefs(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("使用者偏好更新失敗：%s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": ERROR_PREFERENCES_UPDATE_FAILED,
                "detail": t(GENERIC_PREFERENCES_ERROR, lang=lang),
            },
        ) from e
