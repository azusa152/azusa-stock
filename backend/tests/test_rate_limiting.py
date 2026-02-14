"""
Rate limiting tests — verify slowapi rate limits are enforced on write endpoints.
"""

import os
from unittest.mock import patch


def test_rate_limiter_enforces_limits_on_admin_endpoint(client):
    """Admin cache clear endpoint enforces rate limit (10 requests/minute)."""
    test_key = "test-rate-limit-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # First 10 requests should succeed
        for i in range(10):
            response = client.post(
                "/admin/cache/clear", headers={"X-API-Key": test_key}
            )
            assert response.status_code == 200, f"Request {i+1} should succeed"

        # 11th request should be rate limited
        response = client.post("/admin/cache/clear", headers={"X-API-Key": test_key})
        assert response.status_code == 429, "11th request should be rate limited"
        assert "rate limit exceeded" in response.text.lower()


def test_rate_limiter_does_not_affect_read_endpoints(client):
    """Rate limiter does not affect GET endpoints like health checks."""
    # Health endpoint is not rate limited
    for _ in range(20):  # More than typical rate limit
        response = client.get("/health")
        assert response.status_code == 200


def test_rate_limiter_returns_429_with_error_message(client):
    """Rate limiter returns 429 status with descriptive error message."""
    test_key = "test-429-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # Exhaust rate limit
        for _ in range(10):
            client.post("/admin/cache/clear", headers={"X-API-Key": test_key})

        # Next request should return 429
        response = client.post("/admin/cache/clear", headers={"X-API-Key": test_key})
        assert response.status_code == 429
        assert (
            "rate limit" in response.text.lower() or "too many" in response.text.lower()
        )


def test_scan_endpoint_enforces_rate_limit(client):
    """Scan endpoint enforces rate limit (5 requests/minute)."""
    test_key = "test-scan-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # First 5 requests should succeed (200 or 409 if scan already in progress)
        for i in range(5):
            response = client.post("/scan", headers={"X-API-Key": test_key})
            assert response.status_code in [
                200,
                409,
            ], f"Request {i+1} should succeed or conflict"

        # 6th request should be rate limited
        response = client.post("/scan", headers={"X-API-Key": test_key})
        assert response.status_code == 429, "6th request should be rate limited"
        assert "rate limit exceeded" in response.text.lower()


def test_webhook_endpoint_enforces_rate_limit(client):
    """Webhook endpoint enforces rate limit (5 requests/minute)."""
    test_key = "test-webhook-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # First 5 requests should succeed
        for i in range(5):
            response = client.post(
                "/webhook",
                headers={"X-API-Key": test_key},
                json={"action": "help"},
            )
            assert response.status_code == 200, f"Request {i+1} should succeed"

        # 6th request should be rate limited
        response = client.post(
            "/webhook", headers={"X-API-Key": test_key}, json={"action": "help"}
        )
        assert response.status_code == 429, "6th request should be rate limited"
        assert "rate limit exceeded" in response.text.lower()


def test_digest_endpoint_enforces_rate_limit(client):
    """Digest endpoint enforces rate limit (5 requests/minute)."""
    test_key = "test-digest-key"

    with patch.dict(os.environ, {"FOLIO_API_KEY": test_key}, clear=False):
        # First 5 requests should succeed (200 or 409 if digest already in progress)
        for i in range(5):
            response = client.post("/digest", headers={"X-API-Key": test_key})
            assert response.status_code in [
                200,
                409,
            ], f"Request {i+1} should succeed or conflict"

        # 6th request should be rate limited
        response = client.post("/digest", headers={"X-API-Key": test_key})
        assert response.status_code == 429, "6th request should be rate limited"
        assert "rate limit exceeded" in response.text.lower()
