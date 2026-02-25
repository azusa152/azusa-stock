"""
Tests for persona_service.
Uses db_session fixture (in-memory SQLite) — no mocks required for pure CRUD.
"""

import json

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from application.settings.persona_service import (
    create_profile,
    deactivate_profile,
    get_active_profile,
    list_templates,
    update_profile,
)
from domain.constants import DEFAULT_USER_ID
from domain.entities import SystemTemplate, UserInvestmentProfile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LANG = "zh-TW"

_DEFAULT_CONFIG = {"Bond": 30, "Trend_Setter": 40, "Cash": 30}


def _seed_template(
    session: Session,
    template_id: str = "balanced",
    name: str = "Balanced",
    default_config: dict | None = None,
) -> SystemTemplate:
    tmpl = SystemTemplate(
        id=template_id,
        name=name,
        description="A balanced approach",
        quote="Balance is key",
        is_empty=False,
        default_config=json.dumps(default_config or _DEFAULT_CONFIG),
    )
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


def _seed_profile(
    session: Session,
    name: str = "My Profile",
    is_active: bool = True,
    config: dict | None = None,
) -> UserInvestmentProfile:
    profile = UserInvestmentProfile(
        user_id=DEFAULT_USER_ID,
        name=name,
        home_currency="TWD",
        config=json.dumps(config or _DEFAULT_CONFIG),
        is_active=is_active,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _create_payload(**kwargs) -> dict:
    defaults = {
        "name": "My Profile",
        "source_template_id": None,
        "home_currency": "TWD",
        "config": _DEFAULT_CONFIG,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


class TestListTemplates:
    def test_returns_empty_when_no_templates(self, db_session: Session) -> None:
        result = list_templates(db_session)
        assert result == []

    def test_returns_all_templates(self, db_session: Session) -> None:
        _seed_template(db_session, "balanced", "Balanced")
        _seed_template(db_session, "conservative", "Conservative")
        result = list_templates(db_session)
        assert len(result) == 2
        ids = {t["id"] for t in result}
        assert ids == {"balanced", "conservative"}

    def test_template_has_required_keys(self, db_session: Session) -> None:
        _seed_template(db_session)
        result = list_templates(db_session)
        keys = set(result[0].keys())
        assert {
            "id",
            "name",
            "description",
            "quote",
            "is_empty",
            "default_config",
        } <= keys

    def test_default_config_is_parsed_dict(self, db_session: Session) -> None:
        _seed_template(db_session, default_config={"Bond": 50})
        result = list_templates(db_session)
        assert isinstance(result[0]["default_config"], dict)
        assert result[0]["default_config"]["Bond"] == 50


# ---------------------------------------------------------------------------
# get_active_profile
# ---------------------------------------------------------------------------


class TestGetActiveProfile:
    def test_returns_none_when_no_profile(self, db_session: Session) -> None:
        result = get_active_profile(db_session)
        assert result is None

    def test_returns_active_profile(self, db_session: Session) -> None:
        _seed_profile(db_session, name="Active Profile")
        result = get_active_profile(db_session)
        assert result is not None
        assert result["name"] == "Active Profile"
        assert result["is_active"] is True

    def test_does_not_return_inactive_profile(self, db_session: Session) -> None:
        _seed_profile(db_session, is_active=False)
        result = get_active_profile(db_session)
        assert result is None

    def test_config_is_parsed_dict(self, db_session: Session) -> None:
        _seed_profile(db_session, config={"Bond": 40})
        result = get_active_profile(db_session)
        assert isinstance(result["config"], dict)
        assert result["config"]["Bond"] == 40


# ---------------------------------------------------------------------------
# create_profile
# ---------------------------------------------------------------------------


class TestCreateProfile:
    def test_creates_profile_successfully(self, db_session: Session) -> None:
        result = create_profile(db_session, _create_payload(), _LANG)
        assert result["name"] == "My Profile"
        assert result["is_active"] is True
        assert result["id"] is not None

    def test_deactivates_existing_active_profile(self, db_session: Session) -> None:
        old = _seed_profile(db_session, name="Old Profile")
        create_profile(db_session, _create_payload(name="New Profile"), _LANG)

        # Re-fetch old profile to check it was deactivated
        db_session.refresh(old)
        assert old.is_active is False

    def test_only_one_active_profile_after_create(self, db_session: Session) -> None:
        _seed_profile(db_session, name="Old")
        create_profile(db_session, _create_payload(name="New"), _LANG)
        active = get_active_profile(db_session)
        assert active["name"] == "New"

    def test_config_stored_and_returned_as_dict(self, db_session: Session) -> None:
        cfg = {"Bond": 20, "Trend_Setter": 80}
        result = create_profile(db_session, _create_payload(config=cfg), _LANG)
        assert result["config"] == cfg

    def test_stores_source_template_id(self, db_session: Session) -> None:
        result = create_profile(
            db_session, _create_payload(source_template_id="balanced"), _LANG
        )
        assert result["source_template_id"] == "balanced"

    def test_home_currency_stored(self, db_session: Session) -> None:
        result = create_profile(db_session, _create_payload(home_currency="USD"), _LANG)
        assert result["home_currency"] == "USD"


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------


class TestUpdateProfile:
    def test_updates_name(self, db_session: Session) -> None:
        profile = _seed_profile(db_session, name="Original")
        result = update_profile(db_session, profile.id, {"name": "Updated"}, _LANG)
        assert result["name"] == "Updated"

    def test_updates_config(self, db_session: Session) -> None:
        profile = _seed_profile(db_session)
        new_cfg = {"Bond": 100}
        result = update_profile(db_session, profile.id, {"config": new_cfg}, _LANG)
        assert result["config"] == new_cfg

    def test_updates_home_currency(self, db_session: Session) -> None:
        profile = _seed_profile(db_session)
        result = update_profile(db_session, profile.id, {"home_currency": "USD"}, _LANG)
        assert result["home_currency"] == "USD"

    def test_partial_update_preserves_other_fields(self, db_session: Session) -> None:
        profile = _seed_profile(db_session, name="Keep Me")
        result = update_profile(db_session, profile.id, {"home_currency": "JPY"}, _LANG)
        assert result["name"] == "Keep Me"

    def test_raises_404_for_nonexistent_id(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            update_profile(db_session, 99999, {"name": "X"}, _LANG)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "PROFILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# deactivate_profile
# ---------------------------------------------------------------------------


class TestDeactivateProfile:
    def test_deactivates_active_profile(self, db_session: Session) -> None:
        profile = _seed_profile(db_session, is_active=True)
        deactivate_profile(db_session, profile.id, _LANG)
        db_session.refresh(profile)
        assert profile.is_active is False

    def test_returns_message(self, db_session: Session) -> None:
        profile = _seed_profile(db_session)
        result = deactivate_profile(db_session, profile.id, _LANG)
        assert "message" in result

    def test_raises_404_for_nonexistent_id(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            deactivate_profile(db_session, 99999, _LANG)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "PROFILE_NOT_FOUND"

    def test_profile_no_longer_returned_as_active(self, db_session: Session) -> None:
        profile = _seed_profile(db_session)
        deactivate_profile(db_session, profile.id, _LANG)
        result = get_active_profile(db_session)
        assert result is None
