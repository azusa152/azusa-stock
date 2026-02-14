"""
API authentication tests — happy and sad paths for X-API-Key header validation.
"""

import os
from unittest.mock import patch


def test_auth_disabled_when_key_unset(client):
    """Dev mode: requests succeed when FOLIO_API_KEY is unset."""
    with patch.dict(os.environ, {}, clear=False):
        # Remove FOLIO_API_KEY if present
        os.environ.pop("FOLIO_API_KEY", None)
        response = client.get("/stocks")
        assert response.status_code == 200


def test_auth_enabled_valid_key(client):
    """Production mode: requests succeed with valid API key."""
    test_key = "test-secret-key-12345"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        response = client.get("/stocks", headers={"X-API-Key": test_key})
        assert response.status_code == 200


def test_auth_enabled_missing_key(client):
    """Production mode: requests fail without API key header."""
    test_key = "test-secret-key-12345"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        response = client.get("/stocks")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing X-API-Key header"


def test_auth_enabled_invalid_key(client):
    """Production mode: requests fail with wrong API key."""
    correct_key = "correct-secret-key"
    wrong_key = "wrong-secret-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": correct_key}, clear=False):
        response = client.get("/stocks", headers={"X-API-Key": wrong_key})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"


def test_health_endpoint_exempt_from_auth(client):
    """Health check is accessible without API key even when auth is enabled."""
    test_key = "test-health-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # Without key - should still work
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # With key - should also work
        response = client.get("/health", headers={"X-API-Key": test_key})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_webhook_endpoint_requires_auth(client):
    """Webhook endpoint respects auth when enabled."""
    test_key = "test-webhook-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # Without key
        response = client.post("/webhook", json={"action": "help"})
        assert response.status_code == 401

        # With valid key
        response = client.post(
            "/webhook",
            json={"action": "help"},
            headers={"X-API-Key": test_key},
        )
        assert response.status_code == 200


def test_scan_endpoint_requires_auth(client):
    """Scan endpoint respects auth when enabled."""
    test_key = "test-scan-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # Without key
        response = client.post("/scan")
        assert response.status_code == 401

        # With valid key (will get mocked response from conftest patches)
        response = client.post("/scan", headers={"X-API-Key": test_key})
        # Should not be 401 (actual response code depends on scan logic)
        assert response.status_code != 401


def test_cache_clear_endpoint_requires_auth(client):
    """Cache clear endpoint respects auth when enabled."""
    test_key = "test-cache-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # Without key
        response = client.post("/admin/cache/clear")
        assert response.status_code == 401

        # With valid key
        response = client.post("/admin/cache/clear", headers={"X-API-Key": test_key})
        assert response.status_code == 200
