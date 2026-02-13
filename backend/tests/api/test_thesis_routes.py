"""Tests for thesis versioning routes (POST/GET /ticker/{ticker}/thesis)."""


def _create_stock(client, ticker="NVDA", category="Growth", thesis="AI leader"):
    """Helper: create a tracked stock."""
    resp = client.post(
        "/ticker",
        json={
            "ticker": ticker,
            "category": category,
            "thesis": thesis,
        },
    )
    assert resp.status_code == 200
    return resp.json()


class TestCreateThesis:
    """Tests for POST /ticker/{ticker}/thesis."""

    def test_add_thesis_should_succeed(self, client):
        # Arrange
        _create_stock(client)

        # Act
        resp = client.post(
            "/ticker/NVDA/thesis",
            json={
                "content": "Upgraded: data center revenue accelerating",
                "tags": ["AI", "DC"],
            },
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body

    def test_add_thesis_should_return_404_for_unknown_stock(self, client):
        # Act
        resp = client.post(
            "/ticker/UNKNOWN/thesis",
            json={
                "content": "Some thesis",
                "tags": [],
            },
        )

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "STOCK_NOT_FOUND"

    def test_add_thesis_should_return_422_when_missing_content(self, client):
        # Act — missing required 'content' field
        resp = client.post("/ticker/NVDA/thesis", json={"tags": ["AI"]})

        # Assert
        assert resp.status_code == 422

    def test_add_thesis_with_empty_tags_should_succeed(self, client):
        # Arrange
        _create_stock(client)

        # Act
        resp = client.post(
            "/ticker/NVDA/thesis",
            json={
                "content": "Updated view without tags",
            },
        )

        # Assert
        assert resp.status_code == 200


class TestGetThesisHistory:
    """Tests for GET /ticker/{ticker}/thesis."""

    def test_get_history_should_return_initial_thesis(self, client):
        # Arrange — creating stock sets the first thesis
        _create_stock(client, thesis="Initial AI thesis")

        # Act
        resp = client.get("/ticker/NVDA/thesis")

        # Assert
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 1
        assert history[0]["content"] == "Initial AI thesis"

    def test_get_history_should_include_added_thesis(self, client):
        # Arrange
        _create_stock(client, thesis="First view")
        client.post(
            "/ticker/NVDA/thesis",
            json={
                "content": "Second view: upgraded",
                "tags": ["upgrade"],
            },
        )

        # Act
        resp = client.get("/ticker/NVDA/thesis")

        # Assert
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 2
        contents = [h["content"] for h in history]
        assert "First view" in contents
        assert "Second view: upgraded" in contents

    def test_get_history_should_return_404_for_unknown_stock(self, client):
        # Act
        resp = client.get("/ticker/UNKNOWN/thesis")

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "STOCK_NOT_FOUND"
