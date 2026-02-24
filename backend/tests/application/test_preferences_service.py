"""
Tests for preferences_service.
Uses db_session fixture (in-memory SQLite) — no mocks required for pure CRUD.
"""

from sqlmodel import Session

from application.settings.preferences_service import get_preferences, update_preferences
from domain.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_NOTIFICATION_PREFERENCES,
    DEFAULT_USER_ID,
)
from domain.entities import UserPreferences

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LANG = "zh-TW"


def _seed_prefs(
    session: Session,
    language: str = "en",
    privacy_mode: bool = False,
) -> UserPreferences:
    prefs = UserPreferences(
        user_id=DEFAULT_USER_ID,
        language=language,
        privacy_mode=privacy_mode,
    )
    session.add(prefs)
    session.commit()
    session.refresh(prefs)
    return prefs


def _update_payload(**kwargs) -> dict:
    defaults = {
        "language": "en",
        "privacy_mode": False,
        "notification_preferences": None,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# get_preferences
# ---------------------------------------------------------------------------


class TestGetPreferences:
    def test_returns_defaults_when_no_prefs(self, db_session: Session) -> None:
        result = get_preferences(db_session)
        assert result["language"] == DEFAULT_LANGUAGE
        assert result["privacy_mode"] is False
        assert result["notification_preferences"] == DEFAULT_NOTIFICATION_PREFERENCES

    def test_returns_stored_preferences(self, db_session: Session) -> None:
        _seed_prefs(db_session, language="ja", privacy_mode=True)
        result = get_preferences(db_session)
        assert result["language"] == "ja"
        assert result["privacy_mode"] is True

    def test_notification_prefs_fills_missing_keys(self, db_session: Session) -> None:
        _seed_prefs(db_session)
        result = get_preferences(db_session)
        # All default notification keys should be present
        for key in DEFAULT_NOTIFICATION_PREFERENCES:
            assert key in result["notification_preferences"]


# ---------------------------------------------------------------------------
# update_preferences
# ---------------------------------------------------------------------------


class TestUpdatePreferences:
    def test_creates_prefs_when_none_exist(self, db_session: Session) -> None:
        result = update_preferences(db_session, _update_payload(language="en"), _LANG)
        assert result["language"] == "en"
        assert result["privacy_mode"] is False

    def test_updates_existing_prefs(self, db_session: Session) -> None:
        _seed_prefs(db_session, language="en")
        result = update_preferences(
            db_session, _update_payload(language="ja", privacy_mode=True), _LANG
        )
        assert result["language"] == "ja"
        assert result["privacy_mode"] is True

    def test_does_not_change_language_when_none(self, db_session: Session) -> None:
        _seed_prefs(db_session, language="ja")
        result = update_preferences(db_session, _update_payload(language=None), _LANG)
        assert result["language"] == "ja"

    def test_uses_default_language_when_none_on_create(
        self, db_session: Session
    ) -> None:
        result = update_preferences(db_session, _update_payload(language=None), _LANG)
        assert result["language"] == DEFAULT_LANGUAGE

    def test_updates_notification_preferences(self, db_session: Session) -> None:
        _seed_prefs(db_session)
        new_notif = {**DEFAULT_NOTIFICATION_PREFERENCES, "scan_alerts": False}
        result = update_preferences(
            db_session,
            _update_payload(notification_preferences=new_notif),
            _LANG,
        )
        assert result["notification_preferences"]["scan_alerts"] is False

    def test_sets_notification_prefs_on_create(self, db_session: Session) -> None:
        new_notif = {**DEFAULT_NOTIFICATION_PREFERENCES, "weekly_digest": False}
        result = update_preferences(
            db_session,
            _update_payload(notification_preferences=new_notif),
            _LANG,
        )
        assert result["notification_preferences"]["weekly_digest"] is False

    def test_persists_to_database(self, db_session: Session) -> None:
        update_preferences(db_session, _update_payload(language="zh-CN"), _LANG)
        result = get_preferences(db_session)
        assert result["language"] == "zh-CN"

    def test_privacy_mode_toggle(self, db_session: Session) -> None:
        _seed_prefs(db_session, privacy_mode=False)
        result = update_preferences(
            db_session, _update_payload(privacy_mode=True), _LANG
        )
        assert result["privacy_mode"] is True
