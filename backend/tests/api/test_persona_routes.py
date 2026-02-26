"""
Contract tests for persona / profile routes.

Covers the HTTP layer of:
  GET  /personas/templates
  GET  /profiles
  POST /profiles
  PUT  /profiles/{id}
  DELETE /profiles/{id}
"""

from fastapi.testclient import TestClient

_PROFILE_PAYLOAD = {"config": {"Growth": 100}, "home_currency": "USD"}


# ---------------------------------------------------------------------------
# GET /personas/templates
# ---------------------------------------------------------------------------


class TestListPersonaTemplates:
    def test_should_return_200_with_list(self, client: TestClient):
        resp = client.get("/personas/templates")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_each_template_has_required_fields(self, client: TestClient):
        resp = client.get("/personas/templates")
        assert resp.status_code == 200
        for tpl in resp.json():
            assert "id" in tpl
            assert "name" in tpl
            assert "is_empty" in tpl


# ---------------------------------------------------------------------------
# GET /profiles
# ---------------------------------------------------------------------------


class TestGetActiveProfile:
    def test_should_return_none_when_no_profile_exists(self, client: TestClient):
        resp = client.get("/profiles")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_should_return_profile_when_active_profile_exists(self, client: TestClient):
        client.post("/profiles", json=_PROFILE_PAYLOAD)
        resp = client.get("/profiles")
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data["is_active"] is True
        assert data["home_currency"] == "USD"


# ---------------------------------------------------------------------------
# POST /profiles
# ---------------------------------------------------------------------------


class TestCreateProfile:
    def test_should_return_created_profile(self, client: TestClient):
        resp = client.post("/profiles", json=_PROFILE_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["is_active"] is True

    def test_should_deactivate_old_profile_on_create(self, client: TestClient):
        first = client.post("/profiles", json=_PROFILE_PAYLOAD).json()
        client.post("/profiles", json={**_PROFILE_PAYLOAD, "name": "Second"})
        # First profile should now be inactive — verify via GET returns new one
        active = client.get("/profiles").json()
        assert active["id"] != first["id"]


# ---------------------------------------------------------------------------
# PUT /profiles/{id}
# ---------------------------------------------------------------------------


class TestUpdateProfile:
    def test_should_update_profile_name(self, client: TestClient):
        profile_id = client.post("/profiles", json=_PROFILE_PAYLOAD).json()["id"]
        resp = client.put(f"/profiles/{profile_id}", json={"name": "Renamed"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_should_update_home_currency(self, client: TestClient):
        profile_id = client.post("/profiles", json=_PROFILE_PAYLOAD).json()["id"]
        resp = client.put(f"/profiles/{profile_id}", json={"home_currency": "JPY"})
        assert resp.status_code == 200
        assert resp.json()["home_currency"] == "JPY"


# ---------------------------------------------------------------------------
# DELETE /profiles/{id}
# ---------------------------------------------------------------------------


class TestDeleteProfile:
    def test_should_deactivate_profile_and_return_message(self, client: TestClient):
        profile_id = client.post("/profiles", json=_PROFILE_PAYLOAD).json()["id"]
        resp = client.delete(f"/profiles/{profile_id}")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_profile_should_be_gone_after_delete(self, client: TestClient):
        profile_id = client.post("/profiles", json=_PROFILE_PAYLOAD).json()["id"]
        client.delete(f"/profiles/{profile_id}")
        active = client.get("/profiles").json()
        assert active is None
