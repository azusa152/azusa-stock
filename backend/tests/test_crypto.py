"""
Encryption tests — verify Fernet encryption/decryption for sensitive data.
"""

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from infrastructure.crypto import decrypt_token, encrypt_token, is_encrypted


@pytest.fixture
def fernet_key():
    """Generate a temporary Fernet key for testing."""
    return Fernet.generate_key().decode()


def test_encrypt_token_with_valid_key(fernet_key):
    """Encrypt token with valid FERNET_KEY."""
    plaintext = "123456:ABC-DEF1234567890abcdefghijklmnopqrst"

    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        encrypted = encrypt_token(plaintext)

    assert encrypted != plaintext
    assert len(encrypted) > len(plaintext)
    assert encrypted  # Not empty


def test_decrypt_token_with_valid_key(fernet_key):
    """Decrypt token with correct FERNET_KEY."""
    plaintext = "123456:ABC-DEF1234567890abcdefghijklmnopqrst"

    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        encrypted = encrypt_token(plaintext)
        decrypted = decrypt_token(encrypted)

    assert decrypted == plaintext


def test_encrypt_empty_string_returns_empty(fernet_key):
    """Encrypt empty string returns empty string."""
    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        encrypted = encrypt_token("")

    assert encrypted == ""


def test_decrypt_empty_string_returns_empty(fernet_key):
    """Decrypt empty string returns empty string."""
    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        decrypted = decrypt_token("")

    assert decrypted == ""


def test_encrypt_without_fernet_key_raises_error():
    """Encrypt without FERNET_KEY raises ValueError."""
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(ValueError, match="FERNET_KEY 環境變數未設定"),
    ):
        encrypt_token("test_token")


def test_decrypt_with_wrong_key_returns_empty(fernet_key):
    """Decrypt with wrong FERNET_KEY returns empty string (graceful failure)."""
    plaintext = "123456:ABC-DEF1234567890abcdefghijklmnopqrst"

    # Encrypt with one key
    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        encrypted = encrypt_token(plaintext)

    # Try to decrypt with a different key
    wrong_key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"FERNET_KEY": wrong_key}):
        decrypted = decrypt_token(encrypted)

    assert decrypted == ""  # Graceful failure


def test_is_encrypted_detects_encrypted_token(fernet_key):
    """is_encrypted returns True for encrypted tokens."""
    plaintext = "123456:ABC-DEF1234567890abcdefghijklmnopqrst"

    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        encrypted = encrypt_token(plaintext)
        result = is_encrypted(encrypted)

    assert result is True


def test_is_encrypted_detects_plaintext_token(fernet_key):
    """is_encrypted returns False for plaintext tokens."""
    plaintext = "123456:ABC-DEF1234567890abcdefghijklmnopqrst"

    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        result = is_encrypted(plaintext)

    assert result is False


def test_is_encrypted_handles_empty_string():
    """is_encrypted returns False for empty string."""
    assert is_encrypted("") is False


def test_roundtrip_encryption_multiple_tokens(fernet_key):
    """Multiple tokens can be encrypted and decrypted correctly."""
    tokens = [
        "123456:ABC-DEF1234567890abcdefghijklmnopqrst",
        "789012:XYZ-UVW0987654321zyxwvutsrqponmlkji",
        "345678:MNO-PQR5432109876fedcbazyxwvutsrqp",
    ]

    with patch.dict(os.environ, {"FERNET_KEY": fernet_key}):
        encrypted_tokens = [encrypt_token(t) for t in tokens]
        decrypted_tokens = [decrypt_token(e) for e in encrypted_tokens]

    assert decrypted_tokens == tokens
    assert all(e != t for e, t in zip(encrypted_tokens, tokens, strict=True))


def test_telegram_settings_without_fernet_key_stores_plaintext(client):
    """Dev mode: Telegram settings stores plaintext token when FERNET_KEY unset."""
    plaintext_token = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Remove FERNET_KEY to simulate dev mode
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FERNET_KEY", None)

        # Should succeed and store plaintext
        response = client.put(
            "/settings/telegram",
            json={
                "telegram_chat_id": "123456789",
                "custom_bot_token": plaintext_token,
                "use_custom_bot": True,
            },
        )

    assert response.status_code == 200
    data = response.json()
    # Token should be masked even if stored as plaintext
    assert "***" in data["custom_bot_token_masked"]
    # Full token should never appear in response
    assert plaintext_token not in str(data)
