"""API contract tests for crypto routes."""


def test_crypto_search_should_return_results(client, monkeypatch):
    monkeypatch.setattr(
        "api.routes.crypto_routes.search_crypto_coins",
        lambda _q: [
            {
                "id": "bitcoin",
                "symbol": "BTC",
                "name": "Bitcoin",
                "thumb": "https://example.com/btc.png",
                "ticker": "BTC-USD",
            }
        ],
    )

    response = client.get("/crypto/search", params={"q": "bit"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "BTC-USD"


def test_crypto_price_should_return_structured_payload(client, monkeypatch):
    monkeypatch.setattr(
        "api.routes.crypto_routes.get_crypto_price_for_ticker",
        lambda ticker, coingecko_id=None: {
            "ticker": ticker.upper(),
            "coingecko_id": coingecko_id or "bitcoin",
            "price_usd": 100000.0,
            "change_24h_pct": 1.23,
            "market_cap": 100.0,
            "volume_24h": 10.0,
        },
    )

    response = client.get("/crypto/price/BTC-USD")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "BTC-USD"
    assert body["price_usd"] == 100000.0


def test_crypto_price_should_return_404_when_price_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "api.routes.crypto_routes.get_crypto_price_for_ticker",
        lambda ticker, coingecko_id=None: None,
    )

    response = client.get("/crypto/price/UNKNOWN-USD")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error_code"] == "INVALID_INPUT"
