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


def test_delete_net_worth_item_should_return_404_when_not_found(client) -> None:
    resp = client.delete("/net-worth/items/99999")
    assert resp.status_code == 404
