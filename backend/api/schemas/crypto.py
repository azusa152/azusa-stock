"""
API — Crypto schemas.
"""

from pydantic import BaseModel


class CryptoSearchResult(BaseModel):
    id: str
    symbol: str
    name: str
    thumb: str
    ticker: str


class CryptoPrice(BaseModel):
    ticker: str
    coingecko_id: str | None = None
    price_usd: float
    change_24h_pct: float
    market_cap: float = 0.0
    volume_24h: float = 0.0
