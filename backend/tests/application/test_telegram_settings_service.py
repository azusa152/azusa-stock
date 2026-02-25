"""
Tests for telegram_settings_service.
Uses db_session fixture (in-memory SQLite).
Mocks encrypt_token and send_telegram_message_dual.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from application.messaging.telegram_settings_service import (
    _mask_token,
    get_settings,
    send_test_message,
    update_settings,
)
from domain.constants import DEFAULT_USER_ID
from domain.entities import UserTelegramSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LANG = "zh-TW"


def _seed_settings(
    session: Session,
    chat_id: str = "123456",
    custom_bot_token: str | None = None,
    use_custom_bot: bool = False,
) -> UserTelegramSettings:
    settings = UserTelegramSettings(
        user_id=DEFAULT_USER_ID,
        telegram_chat_id=chat_id,
        custom_bot_token=custom_bot_token,
        use_custom_bot=use_custom_bot,
    )
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


# ---------------------------------------------------------------------------
# _mask_token
# ---------------------------------------------------------------------------


class TestMaskToken:
    def test_masks_normal_token(self) -> None:
        assert _mask_token("abcdefghijk") == "abc***ijk"

    def test_short_token_returns_stars(self) -> None:
        assert _mask_token("abc") == "***"

    def test_none_returns_empty_string(self) -> None:
        assert _mask_token(None) == ""

    def test_empty_string_returns_empty(self) -> None:
        assert _mask_token("") == ""


# ---------------------------------------------------------------------------
# get_settings
# ---------------------------------------------------------------------------


class TestGetSettings:
    def test_returns_defaults_when_no_settings(self, db_session: Session) -> None:
        result = get_settings(db_session)
        assert result == {
            "telegram_chat_id": "",
            "custom_bot_token_masked": "",
            "use_custom_bot": False,
        }

    def test_returns_existing_settings(self, db_session: Session) -> None:
        _seed_settings(db_session, chat_id="999888", use_custom_bot=True)
        result = get_settings(db_session)
        assert result["telegram_chat_id"] == "999888"
        assert result["use_custom_bot"] is True

    def test_masks_custom_bot_token(self, db_session: Session) -> None:
        _seed_settings(db_session, custom_bot_token="abcdefghijk")
        result = get_settings(db_session)
        assert result["custom_bot_token_masked"] == "abc***ijk"
        # Raw token not exposed
        assert "custom_bot_token" not in result

    def test_no_token_returns_empty_masked(self, db_session: Session) -> None:
        _seed_settings(db_session)
        result = get_settings(db_session)
        assert result["custom_bot_token_masked"] == ""


# ---------------------------------------------------------------------------
# update_settings
# ---------------------------------------------------------------------------


class TestUpdateSettings:
    def _payload(self, **kwargs) -> dict:
        defaults = {
            "telegram_chat_id": "777666",
            "custom_bot_token": None,
            "use_custom_bot": False,
        }
        defaults.update(kwargs)
        return defaults

    def test_creates_settings_when_none_exist(self, db_session: Session) -> None:
        result = update_settings(db_session, self._payload())
        assert result["telegram_chat_id"] == "777666"
        assert result["use_custom_bot"] is False

    def test_updates_existing_settings(self, db_session: Session) -> None:
        _seed_settings(db_session, chat_id="111")
        result = update_settings(db_session, self._payload(telegram_chat_id="222"))
        assert result["telegram_chat_id"] == "222"

    def test_encrypts_token_when_fernet_key_set(self, db_session: Session) -> None:
        with (
            patch(
                "application.messaging.telegram_settings_service.encrypt_token",
                return_value="encrypted_value",
            ) as mock_encrypt,
            patch.dict("os.environ", {"FERNET_KEY": "somekey"}),
        ):
            result = update_settings(
                db_session, self._payload(custom_bot_token="plaintext_token")
            )
        mock_encrypt.assert_called_once_with("plaintext_token")
        assert result["custom_bot_token_masked"] == "enc***lue"

    def test_stores_plaintext_when_no_fernet_key(self, db_session: Session) -> None:
        import os

        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("FERNET_KEY", None)
            result = update_settings(
                db_session,
                self._payload(custom_bot_token="rawtoken123456789"),
            )
        assert result["custom_bot_token_masked"] == "raw***789"

    def test_does_not_overwrite_token_when_none(self, db_session: Session) -> None:
        _seed_settings(db_session, custom_bot_token="original_token_value_123")
        result = update_settings(db_session, self._payload(custom_bot_token=None))
        # token should remain unchanged — still masked from original
        assert result["custom_bot_token_masked"] == "ori***123"

    def test_persists_to_database(self, db_session: Session) -> None:
        update_settings(db_session, self._payload(telegram_chat_id="555"))
        result2 = get_settings(db_session)
        assert result2["telegram_chat_id"] == "555"


# ---------------------------------------------------------------------------
# send_test_message
# ---------------------------------------------------------------------------


class TestSendTestMessage:
    def test_raises_400_when_no_settings(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            send_test_message(db_session, _LANG)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "TELEGRAM_NOT_CONFIGURED"

    def test_raises_400_when_chat_id_empty(self, db_session: Session) -> None:
        _seed_settings(db_session, chat_id="")
        with pytest.raises(HTTPException) as exc_info:
            send_test_message(db_session, _LANG)
        assert exc_info.value.status_code == 400

    def test_sends_message_successfully(self, db_session: Session) -> None:
        _seed_settings(db_session, chat_id="123456")
        with patch(
            "application.messaging.telegram_settings_service.send_telegram_message_dual"
        ) as mock_send:
            result = send_test_message(db_session, _LANG)
        mock_send.assert_called_once()
        assert "message" in result

    def test_raises_500_when_send_fails(self, db_session: Session) -> None:
        _seed_settings(db_session, chat_id="123456")
        with (
            patch(
                "application.messaging.telegram_settings_service.send_telegram_message_dual",
                side_effect=RuntimeError("network error"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            send_test_message(db_session, _LANG)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error_code"] == "TELEGRAM_SEND_FAILED"
