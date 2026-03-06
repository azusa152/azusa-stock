"""
Infrastructure — Crypto market data adapter (CoinGecko with yfinance fallback).
"""

from __future__ import annotations

import contextlib
import os
import threading
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import diskcache
from cachetools import TTLCache
from curl_cffi import requests as cffi_requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from domain.constants import (
    COINGECKO_API_URL,
    COINGECKO_RATE_LIMIT_CPS,
    CRYPTO_CACHE_MAXSIZE,
    CRYPTO_CACHE_TTL,
    CURL_CFFI_IMPERSONATE,
    DISK_CACHE_DIR,
    DISK_CACHE_SIZE_LIMIT,
    DISK_CRYPTO_TTL,
    DISK_KEY_CRYPTO,
)
from logging_config import get_logger

logger = get_logger(__name__)

_TOP_COIN_TICKER_MAP: dict[str, str] = {
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
    "BNB-USD": "binancecoin",
    "XRP-USD": "ripple",
    "ADA-USD": "cardano",
    "DOGE-USD": "dogecoin",
    "DOT-USD": "polkadot",
    "AVAX-USD": "avalanche-2",
    "LINK-USD": "chainlink",
    "LTC-USD": "litecoin",
    "TRX-USD": "tron",
    "BCH-USD": "bitcoin-cash",
    "XLM-USD": "stellar",
    "NEAR-USD": "near",
    "ATOM-USD": "cosmos",
    "MATIC-USD": "matic-network",
    "UNI-USD": "uniswap",
    "ETC-USD": "ethereum-classic",
    "FIL-USD": "filecoin",
}

_crypto_cache: TTLCache = TTLCache(maxsize=CRYPTO_CACHE_MAXSIZE, ttl=CRYPTO_CACHE_TTL)
_disk_cache = diskcache.Cache(DISK_CACHE_DIR, size_limit=DISK_CACHE_SIZE_LIMIT)

_inflight_lock = threading.Lock()
_inflight_events: dict[str, threading.Event] = {}

_cb_lock = threading.Lock()
_cb_failures = 0
_cb_open_until = 0.0
_CB_FAILURE_THRESHOLD = 3
_CB_COOLDOWN_SECONDS = 1800


class _RateLimiter:
    def __init__(self, calls_per_second: float) -> None:
        self._min_interval = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


_rate_limiter = _RateLimiter(calls_per_second=COINGECKO_RATE_LIMIT_CPS)


def _get_session() -> cffi_requests.Session:
    return cffi_requests.Session(impersonate=CURL_CFFI_IMPERSONATE)


def _disk_get(key: str):
    with contextlib.suppress(Exception):
        return _disk_cache.get(key)
    return None


def _disk_set(key: str, value: Any, ttl: int) -> None:
    with contextlib.suppress(Exception):
        _disk_cache.set(key, value, expire=ttl)


def _is_cb_open() -> bool:
    with _cb_lock:
        return time.monotonic() < _cb_open_until


def _record_success() -> None:
    global _cb_failures
    with _cb_lock:
        _cb_failures = 0


def _record_failure() -> None:
    global _cb_failures, _cb_open_until
    with _cb_lock:
        _cb_failures += 1
        if _cb_failures >= _CB_FAILURE_THRESHOLD:
            _cb_open_until = time.monotonic() + _CB_COOLDOWN_SECONDS
            logger.warning(
                "CoinGecko circuit breaker opened for %d seconds.", _CB_COOLDOWN_SECONDS
            )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    retry=retry_if_exception_type((RuntimeError, OSError, TimeoutError)),
    reraise=True,
)
def _request_json(
    path: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | list[Any]:
    _rate_limiter.wait()
    session = _get_session()
    headers: dict[str, str] = {"accept": "application/json"}
    api_key = os.getenv("COINGECKO_API_KEY", "").strip()
    if api_key:
        headers["x-cg-pro-api-key"] = api_key
    response = session.get(
        f"{COINGECKO_API_URL}{path}",
        params=params,
        headers=headers,
        timeout=10,
    )
    if response.status_code >= 500:
        raise RuntimeError(f"CoinGecko server error: {response.status_code}")
    if response.status_code >= 400:
        raise OSError(f"CoinGecko request failed: {response.status_code}")
    return response.json()


def _deduped_fetch(
    key: str, fetcher: Callable[[], Any], result_getter: Callable[[], Any]
):
    with _inflight_lock:
        if key in _inflight_events:
            event = _inflight_events[key]
            should_wait = True
        else:
            event = threading.Event()
            _inflight_events[key] = event
            should_wait = False

    if should_wait:
        event.wait()
        return result_getter()

    try:
        return fetcher()
    finally:
        event.set()
        with _inflight_lock:
            _inflight_events.pop(key, None)


def _normalize_ticker(ticker: str) -> str:
    t = ticker.strip().upper()
    if "-" not in t:
        t = f"{t}-USD"
    return t


def resolve_coingecko_id(ticker: str, explicit_id: str | None = None) -> str | None:
    if explicit_id:
        return explicit_id
    return _TOP_COIN_TICKER_MAP.get(_normalize_ticker(ticker))


def search_crypto(query: str) -> list[dict[str, str]]:
    q = query.strip()
    if not q:
        return []
    if _is_cb_open():
        return []
    try:
        data = _request_json("/search", {"query": q})
        _record_success()
        coins = data.get("coins", []) if isinstance(data, dict) else []
        result: list[dict[str, str]] = []
        for coin in coins[:15]:
            symbol = str(coin.get("symbol", "")).upper()
            if not symbol:
                continue
            result.append(
                {
                    "id": str(coin.get("id", "")),
                    "symbol": symbol,
                    "name": str(coin.get("name", "")),
                    "thumb": str(coin.get("thumb", "")),
                    "ticker": f"{symbol}-USD",
                }
            )
        return result
    except Exception as exc:
        _record_failure()
        logger.warning("CoinGecko search failed: %s", exc)
        return []


def get_crypto_prices_batch(coin_ids: list[str]) -> dict[str, dict[str, float]]:
    def _as_price_batch(
        value: Any,
    ) -> dict[str, dict[str, float]] | None:
        if not isinstance(value, dict):
            return None
        # Disk cache returns Any; ensure runtime type is mapping before cast.
        return cast("dict[str, dict[str, float]]", value)

    valid_ids = [c.strip() for c in coin_ids if c and c.strip()]
    if not valid_ids:
        return {}
    if _is_cb_open():
        return {}
    unique_ids = sorted(set(valid_ids))
    ids_key = ",".join(unique_ids)
    cache_key = f"{DISK_KEY_CRYPTO}:batch:{ids_key}"
    cached = _crypto_cache.get(cache_key)
    if cached is not None:
        return cached
    disk_cached = _disk_get(cache_key)
    disk_cached_batch = _as_price_batch(disk_cached)
    if disk_cached_batch is not None:
        _crypto_cache[cache_key] = disk_cached_batch
        return disk_cached_batch

    def _fetch():
        data = _request_json(
            "/simple/price",
            {
                "ids": ids_key,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
        )
        if not isinstance(data, dict):
            return {}
        result: dict[str, dict[str, float]] = {}
        for coin_id, row in data.items():
            if not isinstance(row, dict):
                continue
            price = row.get("usd")
            if price is None:
                continue
            result[coin_id] = {
                "price_usd": float(price),
                "change_24h_pct": float(row.get("usd_24h_change") or 0.0),
                "market_cap": float(row.get("usd_market_cap") or 0.0),
                "volume_24h": float(row.get("usd_24h_vol") or 0.0),
            }
        _crypto_cache[cache_key] = result
        _disk_set(cache_key, result, DISK_CRYPTO_TTL)
        return result

    def _get_cached():
        cached_now = _crypto_cache.get(cache_key)
        if cached_now is not None:
            return cached_now
        disk_now = _disk_get(cache_key)
        disk_now_batch = _as_price_batch(disk_now)
        if disk_now_batch is not None:
            _crypto_cache[cache_key] = disk_now_batch
            return disk_now_batch
        return {}

    try:
        result = _deduped_fetch(cache_key, _fetch, _get_cached)
        _record_success()
        return result
    except Exception as exc:
        _record_failure()
        logger.warning("CoinGecko batch price fetch failed: %s", exc)
        return {}


def _fallback_price_from_yfinance(ticker: str) -> dict[str, float] | None:
    try:
        from infrastructure.market_data import get_technical_signals

        signals = get_technical_signals(_normalize_ticker(ticker))
        if not signals or signals.get("error"):
            return None
        price = signals.get("price")
        change = signals.get("change_pct")
        if price is None:
            return None
        return {
            "price_usd": float(price),
            "change_24h_pct": float(change or 0.0),
            "market_cap": 0.0,
            "volume_24h": 0.0,
        }
    except Exception:
        return None


def get_crypto_price(coin_id: str | None, ticker: str) -> dict[str, float] | None:
    if coin_id:
        batch = get_crypto_prices_batch([coin_id])
        if coin_id in batch:
            return batch[coin_id]
    return _fallback_price_from_yfinance(ticker)


def get_crypto_market_data(coin_id: str) -> dict[str, Any] | None:
    if not coin_id:
        return None
    if _is_cb_open():
        return None
    try:
        data = _request_json(
            f"/coins/{coin_id}",
            {"localization": "false", "tickers": "false", "community_data": "false"},
        )
        _record_success()
        if not isinstance(data, dict):
            return None
        market_data = (
            data.get("market_data", {})
            if isinstance(data.get("market_data"), dict)
            else {}
        )
        current_price = (
            market_data.get("current_price", {})
            if isinstance(market_data.get("current_price"), dict)
            else {}
        )
        return {
            "id": str(data.get("id", coin_id)),
            "symbol": str(data.get("symbol", "")).upper(),
            "name": str(data.get("name", "")),
            "price_usd": float(current_price.get("usd") or 0.0),
            "market_cap": float(
                (market_data.get("market_cap") or {}).get("usd") or 0.0
            ),
            "change_24h_pct": float(
                market_data.get("price_change_percentage_24h") or 0.0
            ),
        }
    except Exception as exc:
        _record_failure()
        logger.warning("CoinGecko market-data fetch failed: %s", exc)
        return None


def prewarm_crypto_prices(coin_ids: list[str]) -> None:
    if not coin_ids:
        return
    _ = get_crypto_prices_batch(coin_ids)
