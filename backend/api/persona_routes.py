"""
API — 投資人格 (Persona) 與投資組合配置 (Profile) 路由。
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.schemas import (
    MessageResponse,
    PersonaTemplateResponse,
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from domain.constants import DEFAULT_USER_ID, ERROR_PROFILE_NOT_FOUND
from domain.entities import SystemTemplate, UserInvestmentProfile
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Persona Templates (read-only)
# ---------------------------------------------------------------------------


@router.get(
    "/personas/templates",
    response_model=list[PersonaTemplateResponse],
    summary="List persona templates",
)
def list_persona_templates(
    session: Session = Depends(get_session),
) -> list[PersonaTemplateResponse]:
    """取得所有系統預設投資人格範本。"""
    templates = session.exec(select(SystemTemplate)).all()
    return [
        PersonaTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            quote=t.quote,
            is_empty=t.is_empty,
            default_config=json.loads(t.default_config),
        )
        for t in templates
    ]


# ---------------------------------------------------------------------------
# User Investment Profiles (CRUD)
# ---------------------------------------------------------------------------


@router.get(
    "/profiles",
    response_model=ProfileResponse | None,
    summary="Get active investment profile",
)
def get_active_profile(
    session: Session = Depends(get_session),
) -> ProfileResponse | None:
    """取得目前啟用中的投資組合配置。"""
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()
    if not profile:
        return None
    return _profile_to_response(profile)


@router.post(
    "/profiles", response_model=ProfileResponse, summary="Create an investment profile"
)
def create_profile(
    payload: ProfileCreateRequest,
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """建立新的投資組合配置（同時停用舊的）。"""
    # 停用既有的 active profile
    existing = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).all()
    for p in existing:
        p.is_active = False

    profile = UserInvestmentProfile(
        user_id=DEFAULT_USER_ID,
        name=payload.name,
        source_template_id=payload.source_template_id,
        home_currency=payload.home_currency,
        config=json.dumps(payload.config),
        is_active=True,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    logger.info(
        "建立投資組合配置：%s（來源範本：%s）", payload.name, payload.source_template_id
    )
    return _profile_to_response(profile)


@router.put(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    summary="Update an investment profile",
)
def update_profile(
    profile_id: int,
    payload: ProfileUpdateRequest,
    session: Session = Depends(get_session),
) -> ProfileResponse:
    """更新投資組合配置。"""
    profile = session.get(UserInvestmentProfile, profile_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": "配置不存在。"},
        )
    if payload.name is not None:
        profile.name = payload.name
    if payload.config is not None:
        profile.config = json.dumps(payload.config)
    if payload.home_currency is not None:
        profile.home_currency = payload.home_currency
    profile.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(profile)
    return _profile_to_response(profile)


@router.delete(
    "/profiles/{profile_id}",
    response_model=MessageResponse,
    summary="Deactivate an investment profile",
)
def delete_profile(
    profile_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """停用投資組合配置（軟刪除）。"""
    profile = session.get(UserInvestmentProfile, profile_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ERROR_PROFILE_NOT_FOUND, "detail": "配置不存在。"},
        )
    profile.is_active = False
    session.commit()
    return {"message": f"配置 '{profile.name}' 已停用。"}


def _profile_to_response(profile: UserInvestmentProfile) -> ProfileResponse:
    """將 DB entity 轉為 API response。"""
    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        name=profile.name,
        source_template_id=profile.source_template_id,
        home_currency=profile.home_currency,
        config=json.loads(profile.config),
        is_active=profile.is_active,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )
