"""
Application — Crypto service.
"""

from infrastructure.market_data import (
    get_crypto_market_data,
    get_crypto_price,
    get_crypto_prices_batch,
    resolve_coingecko_id,
    search_crypto,
)


def search_crypto_coins(query: str) -> list[dict]:
    return search_crypto(query)


def get_crypto_holding_prices(holdings: list[dict]) -> dict[str, dict]:
    """
    holdings: [{"ticker": "BTC-USD", "coingecko_id": "bitcoin"}, ...]
    Returns a map keyed by ticker.
    """
    resolved: list[tuple[str, str | None]] = [
        (
            h.get("ticker", ""),
            resolve_coingecko_id(h.get("ticker", ""), h.get("coingecko_id")),
        )
        for h in holdings
    ]
    coin_ids = [coin_id for _ticker, coin_id in resolved if coin_id]
    batch = get_crypto_prices_batch(coin_ids)

    out: dict[str, dict] = {}
    for ticker, coin_id in resolved:
        if not ticker:
            continue
        if coin_id and coin_id in batch:
            out[ticker] = batch[coin_id]
            continue
        fallback = get_crypto_price(coin_id, ticker)
        if fallback:
            out[ticker] = fallback
    return out


def get_crypto_price_for_ticker(
    ticker: str, coingecko_id: str | None = None
) -> dict | None:
    coin_id = resolve_coingecko_id(ticker, coingecko_id)
    price = get_crypto_price(coin_id, ticker)
    if not price:
        return None
    return {"ticker": ticker, "coingecko_id": coin_id, **price}


def get_crypto_details(coin_id: str) -> dict | None:
    return get_crypto_market_data(coin_id)
