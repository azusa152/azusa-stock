"""Tests for net worth routes."""

NET_WORTH_ITEM_PAYLOAD = {
    "name": "Primary Residence",
    "kind": "asset",
    "category": "property",
    "value": 1000000.0,
    "currency": "USD",
}


def test_create_net_worth_item_should_return_200(client) -> None:
    resp = client.post("/net-worth/items", json=NET_WORTH_ITEM_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Primary Residence"
    assert body["kind"] == "asset"


def test_create_net_worth_item_should_accept_minimum_payment(client) -> None:
    resp = client.post(
        "/net-worth/items",
        json={
            "name": "Credit Card",
            "kind": "liability",
            "category": "credit_card",
            "value": 2000.0,
            "currency": "USD",
            "minimum_payment": 120.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["minimum_payment"] == 120.0


def test_get_net_worth_summary_should_return_200(client) -> None:
    client.post("/net-worth/items", json=NET_WORTH_ITEM_PAYLOAD)

    resp = client.get("/net-worth")
    assert resp.status_code == 200
    body = resp.json()
    assert "net_worth" in body
    assert "investment_value" in body
    assert "other_assets_value" in body
    assert "liabilities_value" in body


def test_create_net_worth_item_should_return_422_on_invalid_payload(client) -> None:
    resp = client.post(
        "/net-worth/items",
        json={
            "name": "",
            "kind": "asset",
            "category": "property",
            "value": -1,
            "currency": "USD",
        },
    )
    assert resp.status_code == 422


def test_create_net_worth_item_should_return_422_on_invalid_category(client) -> None:
    resp = client.post(
        "/net-worth/items",
        json={
            "name": "Oops",
            "kind": "asset",
            "category": "mortgage",
            "value": 1,
            "currency": "USD",
        },
    )
    assert resp.status_code == 422


def test_update_net_worth_item_should_return_404_when_not_found(client) -> None:
    resp = client.put("/net-worth/items/99999", json={"value": 100})
    assert resp.status_code == 404


def test_update_net_worth_item_should_accept_minimum_payment(client) -> None:
    create_resp = client.post(
        "/net-worth/items",
        json={
            "name": "Car Loan",
            "kind": "liability",
            "category": "loan",
            "value": 5000.0,
            "currency": "USD",
        },
    )
    item_id = create_resp.json()["id"]
    resp = client.put(
        f"/net-worth/items/{item_id}",
        json={"minimum_payment": 250.0},
    )
    assert resp.status_code == 200
    assert resp.json()["minimum_payment"] == 250.0


def test_get_net_worth_history_should_return_200(client) -> None:
    client.post("/net-worth/items", json=NET_WORTH_ITEM_PAYLOAD)
    client.post("/net-worth/snapshot")

    resp = client.get("/net-worth/history", params={"days": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert "net_worth" in body[0]


def test_delete_net_worth_item_should_return_404_when_not_found(client) -> None:
    resp = client.delete("/net-worth/items/99999")
    assert resp.status_code == 404


def test_get_net_worth_seed_preview_should_return_cash_positions(client) -> None:
    cash_resp = client.post(
        "/holdings/cash",
        json={"currency": "USD", "amount": 1500.0},
    )
    assert cash_resp.status_code == 200

    resp = client.get("/net-worth/seed-preview", params={"display_currency": "USD"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_holdings"] is True
    assert body["cash_value"] >= 1500.0
    assert body["cash_positions"] == [{"currency": "USD", "amount": 1500.0}]


def test_post_net_worth_seed_should_be_idempotent(client) -> None:
    cash_resp = client.post(
        "/holdings/cash",
        json={"currency": "USD", "amount": 1200.0},
    )
    assert cash_resp.status_code == 200

    first = client.post("/net-worth/seed")
    second = client.post("/net-worth/seed")

    assert first.status_code == 200
    assert len(first.json()["created_items"]) == 1
    assert first.json()["created_items"][0]["source"] == "portfolio_cash"
    assert second.status_code == 200
    assert second.json()["created_items"] == []
    assert second.json()["skipped_currencies"] == ["USD"]


def test_post_net_worth_seed_should_return_400_without_cash_holdings(client) -> None:
    resp = client.post("/net-worth/seed")

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error_code"] == "NET_WORTH_SEED_NO_CASH_HOLDINGS"
