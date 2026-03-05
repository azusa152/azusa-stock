"""
Tests for application.portfolio.crypto_service.
"""

from application.portfolio import crypto_service


def test_get_crypto_holding_prices_should_use_batch_first(monkeypatch):
    monkeypatch.setattr(
        crypto_service,
        "resolve_coingecko_id",
        lambda ticker, explicit: explicit or {"BTC-USD": "bitcoin"}.get(ticker),
    )
    monkeypatch.setattr(
        crypto_service,
        "get_crypto_prices_batch",
        lambda ids: (
            {"bitcoin": {"price_usd": 100000.0, "change_24h_pct": 2.0}}
            if "bitcoin" in ids
            else {}
        ),
    )
    monkeypatch.setattr(crypto_service, "get_crypto_price", lambda _id, _ticker: None)

    result = crypto_service.get_crypto_holding_prices(
        [{"ticker": "BTC-USD", "coingecko_id": "bitcoin"}]
    )

    assert "BTC-USD" in result
    assert result["BTC-USD"]["price_usd"] == 100000.0


def test_get_crypto_holding_prices_should_fallback_when_batch_misses(monkeypatch):
    monkeypatch.setattr(
        crypto_service, "resolve_coingecko_id", lambda ticker, _explicit: f"{ticker}-id"
    )
    monkeypatch.setattr(crypto_service, "get_crypto_prices_batch", lambda _ids: {})
    monkeypatch.setattr(
        crypto_service,
        "get_crypto_price",
        lambda _coin_id, ticker: {
            "price_usd": 42.0,
            "change_24h_pct": -1.0,
            "ticker": ticker,
        },
    )

    result = crypto_service.get_crypto_holding_prices(
        [{"ticker": "DOGE-USD", "coingecko_id": None}]
    )

    assert result["DOGE-USD"]["price_usd"] == 42.0
