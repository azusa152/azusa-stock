"""
Tests for CoinGecko crypto adapter.
"""

from infrastructure.market_data import crypto_adapter


def test_search_crypto_should_return_normalized_items(monkeypatch):
    def _fake_request_json(path, params=None):
        assert path == "/search"
        assert params == {"query": "bit"}
        return {
            "coins": [
                {
                    "id": "bitcoin",
                    "symbol": "btc",
                    "name": "Bitcoin",
                    "thumb": "https://example.com/btc.png",
                }
            ]
        }

    monkeypatch.setattr(crypto_adapter, "_request_json", _fake_request_json)
    monkeypatch.setattr(crypto_adapter, "_is_cb_open", lambda: False)

    result = crypto_adapter.search_crypto("bit")

    assert len(result) == 1
    assert result[0]["id"] == "bitcoin"
    assert result[0]["symbol"] == "BTC"
    assert result[0]["ticker"] == "BTC-USD"


def test_get_crypto_prices_batch_should_parse_simple_price_response(monkeypatch):
    def _fake_request_json(path, params=None):
        assert path == "/simple/price"
        return {
            "bitcoin": {
                "usd": 100000,
                "usd_24h_change": 2.5,
                "usd_market_cap": 1900000000000,
                "usd_24h_vol": 30000000000,
            }
        }

    monkeypatch.setattr(crypto_adapter, "_request_json", _fake_request_json)
    monkeypatch.setattr(crypto_adapter, "_is_cb_open", lambda: False)
    crypto_adapter._crypto_cache.clear()

    result = crypto_adapter.get_crypto_prices_batch(["bitcoin"])

    assert "bitcoin" in result
    assert result["bitcoin"]["price_usd"] == 100000.0
    assert result["bitcoin"]["change_24h_pct"] == 2.5


def test_get_crypto_price_should_fallback_to_yfinance_when_id_missing(monkeypatch):
    monkeypatch.setattr(crypto_adapter, "get_crypto_prices_batch", lambda _ids: {})
    monkeypatch.setattr(
        crypto_adapter,
        "_fallback_price_from_yfinance",
        lambda _ticker: {
            "price_usd": 123.0,
            "change_24h_pct": 1.0,
            "market_cap": 0.0,
            "volume_24h": 0.0,
        },
    )

    result = crypto_adapter.get_crypto_price(None, "BTC-USD")

    assert result is not None
    assert result["price_usd"] == 123.0
