"""Tests for GET /health and GET /prewarm-status endpoints."""

from unittest.mock import patch


def test_health_check_should_return_ok(client):
    # Act
    resp = client.get("/health")

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "folio-backend"


def test_prewarm_status_should_return_not_ready_by_default(client):
    # Arrange — prewarm flag not yet set
    with patch("api.routes.scan_routes.is_prewarm_ready", return_value=False):
        # Act
        resp = client.get("/prewarm-status")

    # Assert
    assert resp.status_code == 200
    assert resp.json() == {"ready": False}


def test_prewarm_status_should_return_ready_after_prewarm_completes(client):
    # Arrange — prewarm flag set to True
    with patch("api.routes.scan_routes.is_prewarm_ready", return_value=True):
        # Act
        resp = client.get("/prewarm-status")

    # Assert
    assert resp.status_code == 200
    assert resp.json() == {"ready": True}
