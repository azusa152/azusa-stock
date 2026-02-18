"""Tests for POST /admin/cache/clear endpoint."""


class TestCacheClearEndpoint:
    """Tests for the cache-clearing admin endpoint."""

    def test_cache_clear_should_return_200_with_result(self, client):
        # Act
        resp = client.post("/admin/cache/clear")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["l1_cleared"] == 12
        assert data["l2_cleared"] is True

    def test_cache_clear_should_be_idempotent(self, client):
        # Act — calling twice should work fine
        resp1 = client.post("/admin/cache/clear")
        resp2 = client.post("/admin/cache/clear")

        # Assert
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()
