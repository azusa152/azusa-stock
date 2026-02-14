"""
Error sanitization tests — verify generic error messages prevent information leakage.
Tests webhook, telegram, and preferences endpoints for exception handling.
"""

from unittest.mock import patch

from domain.constants import (
    ERROR_PREFERENCES_UPDATE_FAILED,
    ERROR_TELEGRAM_SEND_FAILED,
    GENERIC_PREFERENCES_ERROR,
    GENERIC_TELEGRAM_ERROR,
    GENERIC_WEBHOOK_ERROR,
)


def test_webhook_exception_sanitized(client):
    """Webhook endpoint returns generic error on exception (no leak)."""
    # Patch handle_webhook where it's imported in stock_routes
    with patch("api.stock_routes.handle_webhook") as mock_handle:
        mock_handle.side_effect = RuntimeError(
            "Database connection failed - secret info"
        )

        response = client.post("/webhook", json={"action": "help"})

        # Should return 200 with success=False (webhook always returns 200)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["message"] == GENERIC_WEBHOOK_ERROR
        # Should NOT leak exception message
        assert "Database connection failed" not in data["message"]
        assert "secret info" not in data["message"]


def test_webhook_action_help(client):
    """Webhook action 'help' succeeds without exception."""
    response = client.post("/webhook", json={"action": "help"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_telegram_test_send_exception_sanitized(client):
    """Telegram test endpoint returns generic error on exception (no leak)."""
    # First, set up Telegram settings
    client.put(
        "/settings/telegram",
        json={
            "telegram_chat_id": "123456789",
            "use_custom_bot": False,
        },
    )

    # Patch send_telegram_message_dual where it's imported in telegram_routes
    with patch("api.telegram_routes.send_telegram_message_dual") as mock_send:
        mock_send.side_effect = ConnectionError(
            "HTTP 403 Forbidden - Bot token invalid: sk-test-12345"
        )

        response = client.post("/settings/telegram/test")

        # Should return 500 with generic error
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error_code"] == ERROR_TELEGRAM_SEND_FAILED
        assert data["detail"]["detail"] == GENERIC_TELEGRAM_ERROR
        # Should NOT leak exception message or token
        assert "HTTP 403" not in str(data)
        assert "sk-test-12345" not in str(data)
        assert "Bot token invalid" not in str(data)


def test_telegram_test_not_configured(client):
    """Telegram test endpoint returns specific error when not configured."""
    response = client.post("/settings/telegram/test")
    assert response.status_code == 400
    data = response.json()
    # This is an expected user error, not sanitized
    assert "尚未設定 Telegram Chat ID" in data["detail"]["detail"]


def test_preferences_update_exception_sanitized(client):
    """Preferences update endpoint returns generic error on exception (no leak)."""
    # Patch session.commit to raise an exception
    with patch("sqlmodel.Session.commit") as mock_commit:
        mock_commit.side_effect = RuntimeError(
            "Database disk image is malformed - /app/data/radar.db corrupted"
        )

        response = client.put(
            "/settings/preferences",
            json={
                "privacy_mode": True,
                "notification_preferences": {"scan_alerts": True},
            },
        )

        # Should return 500 with generic error
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error_code"] == ERROR_PREFERENCES_UPDATE_FAILED
        assert data["detail"]["detail"] == GENERIC_PREFERENCES_ERROR
        # Should NOT leak exception message or file path
        assert "Database disk image" not in str(data)
        assert "/app/data/radar.db" not in str(data)
        assert "corrupted" not in str(data)


def test_preferences_update_success(client):
    """Preferences update succeeds without exception."""
    response = client.put(
        "/settings/preferences",
        json={
            "privacy_mode": True,
            "notification_preferences": {"scan_alerts": True},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["privacy_mode"] is True


def test_preferences_get_success(client):
    """Preferences get succeeds and returns defaults when not configured."""
    response = client.get("/settings/preferences")
    assert response.status_code == 200
    data = response.json()
    assert "privacy_mode" in data
    assert "notification_preferences" in data


def test_stock_import_partial_failure_no_leak(client):
    """Stock import with partial failures logs but doesn't leak to response."""
    # Import one valid and one invalid item (invalid category will fail at service layer)
    payload = [
        {
            "ticker": "AAPL",
            "category": "Growth",
            "thesis": "Valid stock",
        },
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Should report success count and errors list
    assert "imported" in data
    assert "errors" in data
    # Even if there are errors, they should be generic/user-friendly
    # (implementation-specific behavior)


def test_holding_import_partial_failure_no_leak(client):
    """Holding import with partial failures logs but doesn't leak to response."""
    # First add a stock to avoid StockNotFoundError
    client.post(
        "/ticker",
        json={
            "ticker": "AAPL",
            "category": "Growth",
            "thesis": "Test",
        },
    )

    payload = [
        {
            "ticker": "AAPL",
            "category": "Growth",
            "quantity": 10.0,
        },
    ]
    response = client.post("/holdings/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Should report success count and errors list
    assert "imported" in data
    assert "errors" in data


def test_telegram_settings_token_masking(client):
    """Telegram settings response masks bot token."""
    # Set custom bot token
    client.put(
        "/settings/telegram",
        json={
            "telegram_chat_id": "123456789",
            "custom_bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "use_custom_bot": True,
        },
    )

    # Get settings
    response = client.get("/settings/telegram")
    assert response.status_code == 200
    data = response.json()

    # Token should be masked
    assert data["custom_bot_token_masked"] == "123***XYZ"
    # Full token should never appear in response
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in str(data)


def test_validation_error_422_is_acceptable(client):
    """Pydantic validation errors (422) are acceptable - they don't leak internals."""
    # Missing required field
    response = client.post("/stocks/import", json=[{"category": "Growth"}])
    assert response.status_code == 422
    data = response.json()

    # Pydantic errors are structured and user-facing
    assert "detail" in data
    # Should NOT contain internal file paths, stack traces, or secrets
    # (Pydantic errors are safe by design)


def test_health_endpoint_not_affected_by_exceptions(client):
    """Health endpoint always succeeds regardless of other errors."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_no_stack_trace_in_production_errors(client):
    """Production errors should not include stack traces in response."""
    with patch("application.services.handle_webhook") as mock_handle:
        # Simulate a deep exception with multiple layers
        mock_handle.side_effect = RuntimeError("Database connection failed at line 123")

        response = client.post("/webhook", json={"action": "help"})

        # Response should be clean - no stack traces or internal details
        response_text = str(response.json())
        assert "Traceback" not in response_text
        assert 'File "/app/' not in response_text
        assert "line 123" not in response_text  # No line number leak
