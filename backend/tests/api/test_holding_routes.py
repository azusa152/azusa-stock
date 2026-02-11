"""Tests for holding management routes (CRUD + import/export + rebalance)."""


HOLDING_PAYLOAD = {
    "ticker": "NVDA",
    "category": "Growth",
    "quantity": 10,
    "cost_basis": 100.0,
    "broker": "Firstrade",
    "currency": "USD",
    "account_type": "US",
    "is_cash": False,
}

CASH_PAYLOAD = {
    "currency": "TWD",
    "amount": 50000,
    "broker": "玉山",
    "account_type": "TW",
}


def _create_holding(client, payload=None):
    """Helper: create a holding and return its JSON body."""
    resp = client.post("/holdings", json=payload or HOLDING_PAYLOAD)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Holdings CRUD
# ---------------------------------------------------------------------------


class TestCreateHolding:
    """Tests for POST /holdings."""

    def test_create_holding_should_return_created_holding(self, client):
        # Act
        resp = client.post("/holdings", json=HOLDING_PAYLOAD)

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "NVDA"
        assert body["category"] == "Growth"
        assert body["quantity"] == 10
        assert body["is_cash"] is False

    def test_create_holding_should_return_422_when_missing_fields(self, client):
        # Act — missing required 'ticker'
        resp = client.post("/holdings", json={"category": "Growth", "quantity": 5})

        # Assert
        assert resp.status_code == 422


class TestCreateCashHolding:
    """Tests for POST /holdings/cash."""

    def test_create_cash_should_return_cash_holding(self, client):
        # Act
        resp = client.post("/holdings/cash", json=CASH_PAYLOAD)

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "TWD"
        assert body["is_cash"] is True
        assert body["quantity"] == 50000

    def test_create_cash_should_return_422_when_missing_currency(self, client):
        # Act
        resp = client.post("/holdings/cash", json={"amount": 1000})

        # Assert
        assert resp.status_code == 422


class TestListHoldings:
    """Tests for GET /holdings."""

    def test_list_should_return_empty_initially(self, client):
        # Act
        resp = client.get("/holdings")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_should_return_added_holdings(self, client):
        # Arrange
        _create_holding(client)

        # Act
        resp = client.get("/holdings")

        # Assert
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["ticker"] == "NVDA"


class TestUpdateHolding:
    """Tests for PUT /holdings/{holding_id}."""

    def test_update_should_modify_holding(self, client):
        # Arrange
        created = _create_holding(client)
        holding_id = created["id"]

        # Act
        updated_payload = {**HOLDING_PAYLOAD, "quantity": 20, "cost_basis": 150.0}
        resp = client.put(f"/holdings/{holding_id}", json=updated_payload)

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["quantity"] == 20
        assert body["cost_basis"] == 150.0

    def test_update_should_return_404_for_nonexistent_id(self, client):
        # Act
        resp = client.put("/holdings/99999", json=HOLDING_PAYLOAD)

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "HOLDING_NOT_FOUND"


class TestDeleteHolding:
    """Tests for DELETE /holdings/{holding_id}."""

    def test_delete_should_remove_holding(self, client):
        # Arrange
        created = _create_holding(client)
        holding_id = created["id"]

        # Act
        resp = client.delete(f"/holdings/{holding_id}")

        # Assert
        assert resp.status_code == 200
        assert "NVDA" in resp.json()["message"]

        # Verify deletion
        resp2 = client.get("/holdings")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 0

    def test_delete_should_return_404_for_nonexistent_id(self, client):
        # Act
        resp = client.delete("/holdings/99999")

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "HOLDING_NOT_FOUND"


# ---------------------------------------------------------------------------
# Holdings Import / Export
# ---------------------------------------------------------------------------


class TestExportHoldings:
    """Tests for GET /holdings/export."""

    def test_export_should_return_empty_list_when_no_holdings(self, client):
        # Act
        resp = client.get("/holdings/export")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_export_should_return_all_holdings(self, client):
        # Arrange
        _create_holding(client)
        client.post("/holdings/cash", json=CASH_PAYLOAD)

        # Act
        resp = client.get("/holdings/export")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        tickers = {item["ticker"] for item in data}
        assert tickers == {"NVDA", "TWD"}


class TestImportHoldings:
    """Tests for POST /holdings/import."""

    def test_import_should_replace_all_holdings(self, client):
        # Arrange — create initial holding
        _create_holding(client)

        import_data = [
            {"ticker": "AAPL", "category": "Growth", "quantity": 5, "currency": "USD"},
            {"ticker": "GOOGL", "category": "Moat", "quantity": 3, "currency": "USD"},
        ]

        # Act
        resp = client.post("/holdings/import", json=import_data)

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["imported"] == 2
        assert body["errors"] == []

        # Verify old holdings replaced
        holdings = client.get("/holdings").json()
        tickers = {h["ticker"] for h in holdings}
        assert "NVDA" not in tickers
        assert tickers == {"AAPL", "GOOGL"}

    def test_import_should_handle_empty_list(self, client):
        # Arrange — create initial holding
        _create_holding(client)

        # Act — import empty list (clears everything)
        resp = client.post("/holdings/import", json=[])

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["imported"] == 0

        # Verify all cleared
        holdings = client.get("/holdings").json()
        assert len(holdings) == 0
