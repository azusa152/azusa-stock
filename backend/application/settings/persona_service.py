"""
Application — Persona Service。
封裝投資人格範本查詢與使用者投資組合配置 CRUD 邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from domain.constants import DEFAULT_USER_ID, ERROR_PROFILE_NOT_FOUND
from domain.entities import UserInvestmentProfile
from i18n import t
from infrastructure import repositories as repo
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _profile_to_dict(profile: UserInvestmentProfile) -> dict:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "name": profile.name,
        "source_template_id": profile.source_template_id,
        "home_currency": profile.home_currency,
        "config": json.loads(profile.config),
        "is_active": profile.is_active,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_templates(session: Session) -> list[dict]:
    """Return all system persona templates."""
    templates = repo.find_system_templates(session)
    return [
        {
            "id": tmpl.id,
            "name": tmpl.name,
            "description": tmpl.description,
            "quote": tmpl.quote,
            "is_empty": tmpl.is_empty,
            "default_config": json.loads(tmpl.default_config),
        }
        for tmpl in templates
    ]


def get_active_profile(session: Session) -> dict | None:
    """Return the active investment profile, or None."""
    profile = repo.find_active_profile(session)
    if not profile:
        return None
    return _profile_to_dict(profile)


def create_profile(session: Session, payload: dict, lang: str) -> dict:
    """Create a new investment profile. Deactivates any existing active profile."""
    # Deactivate existing active profiles
    from sqlmodel import select

    existing = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).all()
    for p in existing:
        p.is_active = False

    profile = UserInvestmentProfile(
        user_id=DEFAULT_USER_ID,
        name=payload["name"],
        source_template_id=payload.get("source_template_id"),
        home_currency=payload["home_currency"],
        config=json.dumps(payload["config"]),
        is_active=True,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    logger.info(
        "建立投資組合配置：%s（來源範本：%s）",
        payload["name"],
        payload.get("source_template_id"),
    )
    return _profile_to_dict(profile)


def update_profile(session: Session, profile_id: int, payload: dict, lang: str) -> dict:
    """Update an existing profile. Raises HTTPException 404 if not found."""
    profile = repo.find_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_PROFILE_NOT_FOUND,
                "detail": t("api.profile_not_found", lang=lang),
            },
        )
    if payload.get("name") is not None:
        profile.name = payload["name"]
    if payload.get("config") is not None:
        profile.config = json.dumps(payload["config"])
    if payload.get("home_currency") is not None:
        profile.home_currency = payload["home_currency"]
    profile.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(profile)
    return _profile_to_dict(profile)


def deactivate_profile(session: Session, profile_id: int, lang: str) -> dict:
    """Soft-delete (deactivate) a profile. Raises HTTPException 404 if not found."""
    profile = repo.find_profile_by_id(session, profile_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_PROFILE_NOT_FOUND,
                "detail": t("api.profile_not_found", lang=lang),
            },
        )
    profile.is_active = False
    session.commit()
    return {"message": t("api.profile_deactivated", lang=lang, name=profile.name)}
