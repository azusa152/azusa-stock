"""
Infrastructure — 市場資料適配器 (yfinance)。
負責外部 API 呼叫、快取管理、速率限制。
所有呼叫皆以 try/except 包裹，失敗時回傳結構化降級結果。
含 tenacity 重試機制，針對暫時性網路 / DNS 錯誤自動指數退避重試。
"""

import contextlib
import math
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import TypeVar

import diskcache
import yfinance as yf
from cachetools import TTLCache
from curl_cffi import requests as cffi_requests
from curl_cffi.curl import CurlError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from domain.analysis import (
    classify_vix,
    compute_bias,
    compute_composite_fear_greed,
    compute_daily_change_pct,
    compute_moving_average,
    compute_rsi,
    compute_volume_ratio,
    determine_market_sentiment,
    determine_moat_status,
)
from domain.constants import (
    BETA_CACHE_MAXSIZE,
    BETA_CACHE_TTL,
    CNN_FG_API_URL,
    CNN_FG_REQUEST_TIMEOUT,
    CURL_CFFI_IMPERSONATE,
    DEFAULT_LANGUAGE,
    DISK_BETA_TTL,
    DISK_CACHE_DIR,
    DISK_CACHE_SIZE_LIMIT,
    DISK_DIVIDEND_TTL,
    DISK_EARNINGS_TTL,
    DISK_ETF_HOLDINGS_TTL,
    DISK_ETF_SECTOR_WEIGHTS_TTL,
    DISK_FEAR_GREED_TTL,
    DISK_FOREX_HISTORY_LONG_TTL,
    DISK_FOREX_HISTORY_TTL,
    DISK_FOREX_TTL,
    DISK_KEY_BETA,
    DISK_KEY_DIVIDEND,
    DISK_KEY_EARNINGS,
    DISK_KEY_ETF_HOLDINGS,
    DISK_KEY_ETF_SECTOR_WEIGHTS,
    DISK_KEY_FEAR_GREED,
    DISK_KEY_FOREX,
    DISK_KEY_FOREX_HISTORY,
    DISK_KEY_FOREX_HISTORY_LONG,
    DISK_KEY_MOAT,
    DISK_KEY_PRICE_HISTORY,
    DISK_KEY_PRICE_PAIR,
    DISK_KEY_ROGUE_WAVE,
    DISK_KEY_SECTOR,
    DISK_KEY_SIGNALS,
    DISK_MOAT_TTL,
    DISK_PRICE_HISTORY_TTL,
    DISK_PRICE_PAIR_TTL,
    DISK_ROGUE_WAVE_TTL,
    DISK_SECTOR_TTL,
    DISK_SIGNALS_TTL,
    DIVIDEND_CACHE_MAXSIZE,
    DIVIDEND_CACHE_TTL,
    EARNINGS_CACHE_MAXSIZE,
    EARNINGS_CACHE_TTL,
    ETF_HOLDINGS_CACHE_MAXSIZE,
    ETF_HOLDINGS_CACHE_TTL,
    ETF_TOP_N,
    FEAR_GREED_CACHE_MAXSIZE,
    FEAR_GREED_CACHE_TTL,
    FOREX_CACHE_MAXSIZE,
    FOREX_CACHE_TTL,
    FOREX_HISTORY_CACHE_MAXSIZE,
    FOREX_HISTORY_CACHE_TTL,
    FOREX_HISTORY_LONG_CACHE_MAXSIZE,
    FOREX_HISTORY_LONG_CACHE_TTL,
    FX_HISTORY_PERIOD,
    FX_LONG_TERM_PERIOD,
    INSTITUTIONAL_HOLDERS_TOP_N,
    MA60_WINDOW,
    MA200_WINDOW,
    MARGIN_TREND_QUARTERS,
    MIN_CLOSE_PRICES_FOR_CHANGE,
    MIN_HISTORY_DAYS_FOR_SIGNALS,
    MOAT_CACHE_MAXSIZE,
    MOAT_CACHE_TTL,
    NIKKEI_VI_EXTREME_FEAR,
    NIKKEI_VI_FEAR,
    NIKKEI_VI_GREED,
    NIKKEI_VI_NEUTRAL_LOW,
    NIKKEI_VI_TICKER,
    PRICE_HISTORY_CACHE_MAXSIZE,
    PRICE_HISTORY_CACHE_TTL,
    ROGUE_WAVE_CACHE_MAXSIZE,
    ROGUE_WAVE_CACHE_TTL,
    ROGUE_WAVE_HISTORY_PERIOD,
    ROGUE_WAVE_MIN_HISTORY_DAYS,
    SCAN_THREAD_POOL_SIZE,
    SIGNALS_CACHE_MAXSIZE,
    SIGNALS_CACHE_TTL,
    TWII_TICKER,
    TWII_VOL_EXTREME_FEAR,
    TWII_VOL_FEAR,
    TWII_VOL_GREED,
    TWII_VOL_NEUTRAL_LOW,
    VIX_HISTORY_PERIOD,
    VIX_TICKER,
    YFINANCE_HISTORY_PERIOD,
    YFINANCE_RATE_LIMIT_CPS,
    YFINANCE_RETRY_ATTEMPTS,
    YFINANCE_RETRY_WAIT_MAX,
    YFINANCE_RETRY_WAIT_MIN,
)
from domain.enums import FearGreedLevel, MarketSentiment, MoatStatus
from domain.formatters import build_moat_details, build_signal_status
from i18n import t
from logging_config import get_logger

T = TypeVar("T")

logger = get_logger(__name__)

_BEARISH_TIERS: frozenset = frozenset(
    {MarketSentiment.BEARISH, MarketSentiment.STRONG_BEARISH}
)


# ---------------------------------------------------------------------------
# Retry Decorator：針對暫時性網路/DNS 錯誤自動指數退避重試
# ---------------------------------------------------------------------------
_RETRYABLE_EXCEPTIONS = (CurlError, ConnectionError, OSError)

_yf_retry = retry(
    stop=stop_after_attempt(YFINANCE_RETRY_ATTEMPTS),
    wait=wait_exponential(min=YFINANCE_RETRY_WAIT_MIN, max=YFINANCE_RETRY_WAIT_MAX),
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    reraise=True,
)


def _is_error_dict(result) -> bool:
    """判斷 fetcher 結果是否為錯誤回應（含 'error' 鍵的 dict）。"""
    return isinstance(result, dict) and "error" in result


def _is_dividend_error(result) -> bool:
    """判斷股息 fetcher 結果是否為錯誤。
    ytd_dividend_per_share 為 None 表示 yfinance 呼叫異常（非股息股的合法回應為 0.0）。
    """
    return isinstance(result, dict) and result.get("ytd_dividend_per_share") is None


# ---------------------------------------------------------------------------
# Rate Limiter：限制 yfinance (Yahoo Finance) 呼叫頻率，避免被封鎖
# ---------------------------------------------------------------------------


class RateLimiter:
    """Thread-safe rate limiter，確保呼叫間隔不低於 min_interval。"""

    def __init__(self, calls_per_second: float = YFINANCE_RATE_LIMIT_CPS):
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


_rate_limiter = RateLimiter(calls_per_second=YFINANCE_RATE_LIMIT_CPS)


# ---------------------------------------------------------------------------
# In-flight 重複請求去重：避免同一 key 並發觸發多次 yfinance 呼叫
# ---------------------------------------------------------------------------
_inflight_lock = threading.Lock()
_inflight_events: dict[str, threading.Event] = {}


def _deduped_fetch(
    key: str, fetcher: Callable[[], T], result_getter: Callable[[], T]
) -> T:
    """確保同一 key 的 yfinance 呼叫在任意時刻只有一個在飛行中。

    若已有相同 key 的請求進行中，等待其完成後透過 result_getter 取用結果（例如讀 L1 快取）。

    Args:
        key: 唯一識別此請求的字串（通常為 disk_prefix:ticker）。
        fetcher: 實際執行 yfinance 呼叫並寫入快取的函式。
        result_getter: 等待完成後用來讀取快取結果的函式（fetcher 寫入後呼叫）。
    """
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
        # fetcher 已將結果寫入快取；透過 result_getter 取得
        return result_getter()

    try:
        return fetcher()
    finally:
        # set() before pop(): any late-arriving thread that finds this event already set
        # calls result_getter() and reads L1 — no redundant yfinance call.
        event.set()
        with _inflight_lock:
            _inflight_events.pop(key, None)


# ---------------------------------------------------------------------------
# L1 快取（記憶體）：避免每次頁面載入都重複呼叫 yfinance
# ---------------------------------------------------------------------------
_signals_cache: TTLCache = TTLCache(
    maxsize=SIGNALS_CACHE_MAXSIZE, ttl=SIGNALS_CACHE_TTL
)
_moat_cache: TTLCache = TTLCache(maxsize=MOAT_CACHE_MAXSIZE, ttl=MOAT_CACHE_TTL)
_earnings_cache: TTLCache = TTLCache(
    maxsize=EARNINGS_CACHE_MAXSIZE, ttl=EARNINGS_CACHE_TTL
)
_dividend_cache: TTLCache = TTLCache(
    maxsize=DIVIDEND_CACHE_MAXSIZE, ttl=DIVIDEND_CACHE_TTL
)
_price_history_cache: TTLCache = TTLCache(
    maxsize=PRICE_HISTORY_CACHE_MAXSIZE, ttl=PRICE_HISTORY_CACHE_TTL
)
_forex_cache: TTLCache = TTLCache(maxsize=FOREX_CACHE_MAXSIZE, ttl=FOREX_CACHE_TTL)
_etf_holdings_cache: TTLCache = TTLCache(
    maxsize=ETF_HOLDINGS_CACHE_MAXSIZE, ttl=ETF_HOLDINGS_CACHE_TTL
)
_etf_sector_weights_cache: TTLCache = TTLCache(
    maxsize=ETF_HOLDINGS_CACHE_MAXSIZE, ttl=ETF_HOLDINGS_CACHE_TTL
)
_forex_history_cache: TTLCache = TTLCache(
    maxsize=FOREX_HISTORY_CACHE_MAXSIZE, ttl=FOREX_HISTORY_CACHE_TTL
)
_forex_history_long_cache: TTLCache = TTLCache(
    maxsize=FOREX_HISTORY_LONG_CACHE_MAXSIZE, ttl=FOREX_HISTORY_LONG_CACHE_TTL
)
_fear_greed_cache: TTLCache = TTLCache(
    maxsize=FEAR_GREED_CACHE_MAXSIZE, ttl=FEAR_GREED_CACHE_TTL
)
_beta_cache: TTLCache = TTLCache(maxsize=BETA_CACHE_MAXSIZE, ttl=BETA_CACHE_TTL)
_rogue_wave_cache: TTLCache = TTLCache(
    maxsize=ROGUE_WAVE_CACHE_MAXSIZE, ttl=ROGUE_WAVE_CACHE_TTL
)


# ---------------------------------------------------------------------------
# L2 快取（磁碟）：容器重啟後仍可使用，避免冷啟動時大量呼叫 yfinance
# ---------------------------------------------------------------------------
_disk_cache = diskcache.Cache(DISK_CACHE_DIR, size_limit=DISK_CACHE_SIZE_LIMIT)


def _disk_get(key: str):
    """從磁碟快取 (L2) 讀取。失敗時回傳 None（非致命）。"""
    try:
        return _disk_cache.get(key)
    except Exception:
        return None


def _disk_set(key: str, value, ttl: int) -> None:
    """寫入磁碟快取 (L2)。失敗時靜默跳過（非致命）。"""
    with contextlib.suppress(Exception):
        _disk_cache.set(key, value, expire=ttl)


def clear_all_caches() -> dict:
    """清除所有 L1 記憶體快取與 L2 磁碟快取。"""
    l1_caches = [
        _signals_cache,
        _moat_cache,
        _earnings_cache,
        _dividend_cache,
        _price_history_cache,
        _forex_cache,
        _etf_holdings_cache,
        _etf_sector_weights_cache,
        _forex_history_cache,
        _forex_history_long_cache,
        _fear_greed_cache,
        _beta_cache,
        _rogue_wave_cache,
    ]
    for cache in l1_caches:
        cache.clear()
    _disk_cache.clear()
    logger.info("已清除所有快取（L1×%d + L2 磁碟）。", len(l1_caches))
    return {"l1_cleared": len(l1_caches), "l2_cleared": True}


def _cached_fetch(
    l1_cache: TTLCache,
    ticker: str,
    disk_prefix: str,
    disk_ttl: int,
    fetcher: Callable[[str], T],
    is_error: Callable[[T], bool] | None = None,
) -> T:
    """
    通用二層快取取得函式。
    L1 (記憶體) → L2 (磁碟) → fetcher (yfinance)，並回寫兩層快取。

    is_error — 可選回呼函式，判斷 fetcher 結果是否為錯誤。
    若為錯誤，仍寫入 L1（短暫快取避免瞬間重複呼叫），但略過 L2/磁碟寫入，
    讓下次 L1 過期後可重新嘗試取得正確結果。
    """
    cached = l1_cache.get(ticker)
    if cached is not None:
        # If L1 has an error entry but L2 may have recovered valid data, fall through.
        if is_error is None or not is_error(cached):
            logger.debug("%s 命中 L1 快取（prefix=%s）。", ticker, disk_prefix)
            return cached
        logger.debug(
            "%s L1 為錯誤結果，繼續嘗試 L2（prefix=%s）。", ticker, disk_prefix
        )

    disk_key = f"{disk_prefix}:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("%s 命中 L2 磁碟快取（prefix=%s）。", ticker, disk_prefix)
        l1_cache[ticker] = disk_cached
        return disk_cached

    logger.debug("%s L1+L2 皆未命中（prefix=%s），呼叫 fetcher...", ticker, disk_prefix)

    def _do_fetch() -> T:
        res = fetcher(ticker)
        l1_cache[ticker] = res
        if is_error is not None and is_error(res):
            logger.debug("%s 結果含錯誤，略過寫入 L2 磁碟快取。", ticker)
        else:
            _disk_set(disk_key, res, disk_ttl)
        return res

    def _get_cached() -> T:
        # fetcher 已寫入 L1（成功路徑）；直接讀取即可。
        # 注意：接受 is_error 結果 — fetcher 可能寫了一個錯誤哨兵，這也是合法快取。
        cached = l1_cache.get(ticker)
        if cached is not None:
            return cached  # type: ignore[return-value]
        disk_val = _disk_get(disk_key)
        if disk_val is not None:
            l1_cache[ticker] = disk_val
            return disk_val  # type: ignore[return-value]
        # fetcher 拋出例外（非錯誤哨兵）— 每個等待者各自重試一次（已由速率限制器節流）
        return fetcher(ticker)

    return _deduped_fetch(disk_key, _do_fetch, _get_cached)


def _get_session() -> cffi_requests.Session:
    """建立模擬 Chrome 瀏覽器的 Session，以繞過 Yahoo Finance 的 bot 防護。"""
    return cffi_requests.Session(impersonate=CURL_CFFI_IMPERSONATE)


# ---------------------------------------------------------------------------
# Retryable yfinance network helpers
# ---------------------------------------------------------------------------


@_yf_retry
def _yf_history(ticker: str, period: str):
    """
    取得 yfinance 歷史資料（含重試）。
    空結果也視為可重試：yfinance 有時會吞掉 CurlError/SSL 錯誤，
    僅回傳空 DataFrame 而不拋出例外，導致 @_yf_retry 無法觸發。
    """
    _rate_limiter.wait()
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    hist = stock.history(period=period)
    if hist.empty:
        raise OSError(
            f"{ticker}: yfinance returned empty history, possibly due to a swallowed network error"
        )
    return stock, hist


@_yf_retry
def _yf_quarterly_financials(ticker: str):
    """取得 yfinance 季度財報（含重試）。"""
    _rate_limiter.wait()
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.quarterly_financials


@_yf_retry
def _yf_calendar(ticker: str):
    """取得 yfinance 財報日曆（含重試）。"""
    _rate_limiter.wait()
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.calendar


@_yf_retry
def _yf_info(ticker: str):
    """取得 yfinance 股票 info（含重試）。"""
    _rate_limiter.wait()
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.info or {}


def detect_is_etf(ticker: str) -> bool:
    """透過 yfinance quoteType 偵測是否為 ETF。失敗時回傳 False。"""
    try:
        info = _yf_info(ticker)
        return info.get("quoteType", "") == "ETF"
    except Exception:
        return False


@_yf_retry
def _yf_history_short(ticker: str, period: str = "5d"):
    """取得 yfinance 短期歷史（匯率等，含重試）。
    空結果視為可重試（與 _yf_history 相同理由）。
    """
    _rate_limiter.wait()
    session = _get_session()
    ticker_obj = yf.Ticker(ticker, session=session)
    hist = ticker_obj.history(period=period)
    if hist.empty:
        raise OSError(
            f"{ticker}: yfinance returned empty short history, possibly due to a swallowed network error"
        )
    return hist


@_yf_retry
def _yf_ticker_obj(ticker: str):
    """建立 yfinance Ticker 物件（含重試）。用於 ETF funds_data 等屬性存取。"""
    _rate_limiter.wait()
    return yf.Ticker(ticker, session=_get_session())


@_yf_retry
def _yf_dividend_data(ticker: str) -> tuple[dict, object]:
    """從單一 Ticker 物件取得 info 與股息歷史（含重試）。
    合併兩次呼叫以避免重複建立 session，同時保留重試保護。
    """
    _rate_limiter.wait()
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    info = stock.info or {}
    _rate_limiter.wait()
    dividends = stock.get_dividends()
    return info, dividends


# ===========================================================================
# 技術面訊號
# ===========================================================================


def _fetch_signals_from_yf(ticker: str, pre_fetched_hist=None) -> dict:
    """實際從 yfinance 取得技術訊號（供 _cached_fetch 使用）。
    pre_fetched_hist: 若提供，略過 _yf_history 呼叫，直接使用此 DataFrame（批次掃描優化路徑）。
    機構持倉仍需個別 Ticker 呼叫（best-effort）。
    """
    try:
        if pre_fetched_hist is not None:
            hist = pre_fetched_hist
            _rate_limiter.wait()
            stock = yf.Ticker(ticker, session=_get_session())
        else:
            stock, hist = _yf_history(ticker, YFINANCE_HISTORY_PERIOD)

        if hist.empty or len(hist) < MIN_HISTORY_DAYS_FOR_SIGNALS:
            logger.warning(
                "%s 歷史資料不足（%d 筆），無法計算技術指標。", ticker, len(hist)
            )
            return {
                "error": t(
                    "market.insufficient_history", lang=DEFAULT_LANGUAGE, ticker=ticker
                )
            }

        # Piggyback：將收盤價歷史寫入 price_history 快取，避免後續重複呼叫 yfinance
        _piggyback_price_history(ticker, hist)

        closes = hist["Close"].tolist()
        volumes = hist["Volume"].tolist() if "Volume" in hist.columns else []
        current_price = round(closes[-1], 2)

        # 計算日漲跌（前一交易日 vs. 當日收盤價）
        previous_close = None
        change_pct = None
        if len(closes) >= MIN_CLOSE_PRICES_FOR_CHANGE:
            previous_close = round(closes[-2], 2)
            change_pct = compute_daily_change_pct(current_price, previous_close)
            logger.debug(
                "%s 日漲跌：previous=%.2f, current=%.2f, change=%.2f%%",
                ticker,
                previous_close,
                current_price,
                change_pct if change_pct is not None else 0.0,
            )
        else:
            logger.debug(
                "%s 歷史資料不足（%d 筆），無法計算日漲跌", ticker, len(closes)
            )

        # 使用 domain 層的純計算函式
        rsi = compute_rsi(closes)
        ma200 = compute_moving_average(closes, MA200_WINDOW)
        ma60 = compute_moving_average(closes, MA60_WINDOW)
        bias = compute_bias(current_price, ma60) if ma60 else None
        bias_200 = compute_bias(current_price, ma200) if ma200 else None
        volume_ratio = compute_volume_ratio(volumes)

        logger.info(
            "%s 技術訊號：price=%.2f, RSI=%s, 200MA=%s, 60MA=%s, Bias=%s%%, Bias200=%s%%, VolRatio=%s",
            ticker,
            current_price,
            rsi,
            ma200,
            ma60,
            bias,
            bias_200,
            volume_ratio,
        )

        # 機構持倉 (best-effort，失敗不影響整體回傳)
        institutional_holders = None
        try:
            _rate_limiter.wait()
            holders_df = stock.institutional_holders
            if holders_df is not None and not holders_df.empty:
                top5 = holders_df.head(INSTITUTIONAL_HOLDERS_TOP_N)
                institutional_holders = []
                for _, row in top5.iterrows():
                    holder_entry = {}
                    for col in top5.columns:
                        val = row[col]
                        # 將 Timestamp / NaT 等轉為字串
                        if hasattr(val, "isoformat"):
                            holder_entry[col] = val.isoformat()[:10]
                        elif val is None or (
                            hasattr(val, "item") and str(val) == "NaT"
                        ):
                            holder_entry[col] = "N/A"
                        else:
                            holder_entry[col] = (
                                val if not hasattr(val, "item") else val.item()
                            )
                    institutional_holders.append(holder_entry)
                logger.debug(
                    "%s 機構持倉：取得 %d 筆", ticker, len(institutional_holders)
                )
        except Exception as holder_err:
            logger.debug("%s 機構持倉取得失敗（非致命）：%s", ticker, holder_err)

        raw_signals = {
            "ticker": ticker,
            "price": current_price,
            "previous_close": previous_close,
            "change_pct": change_pct,
            "rsi": rsi,
            "ma200": ma200,
            "ma60": ma60,
            "bias": bias,
            "bias_200": bias_200,
            "volume_ratio": volume_ratio,
            "institutional_holders": institutional_holders,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        return {**raw_signals, "status": build_signal_status(raw_signals)}

    except Exception as e:
        logger.error("無法取得 %s 技術訊號：%s", ticker, e, exc_info=True)
        return {
            "error": t(
                "market.signals_fetch_error",
                lang=DEFAULT_LANGUAGE,
                ticker=ticker,
                error=str(e),
            )
        }


def get_technical_signals(ticker: str) -> dict | None:
    """
    取得技術面訊號：RSI(14)、現價、200MA、60MA、Bias(%)、Volume Ratio。
    結果快取 5 分鐘。錯誤結果僅寫入 L1（短暫），不寫入 L2/磁碟。
    """
    return _cached_fetch(
        _signals_cache,
        ticker,
        DISK_KEY_SIGNALS,
        DISK_SIGNALS_TTL,
        _fetch_signals_from_yf,
        is_error=_is_error_dict,
    )


def batch_download_history(
    tickers: list[str], period: str = YFINANCE_HISTORY_PERIOD
) -> dict:
    """
    使用 yf.download() 一次批次下載多檔股票的價格歷史，大幅減少 HTTP 請求數量。
    回傳 {ticker: DataFrame}，僅包含有效且資料量足夠的股票。
    失敗時靜默回傳空字典（呼叫端應回退至個別呼叫）。
    """
    if not tickers:
        return {}
    try:
        _rate_limiter.wait()
        data = yf.download(
            tickers,
            period=period,
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=True,
        )
        result: dict = {}
        for ticker in tickers:
            try:
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(how="all")
                if not df.empty and len(df) >= MIN_HISTORY_DAYS_FOR_SIGNALS:
                    result[ticker] = df
                else:
                    logger.debug(
                        "%s 批次下載資料不足（%d 筆），將回退至個別呼叫。",
                        ticker,
                        len(df),
                    )
            except (KeyError, Exception) as e:
                logger.debug("批次下載 %s 資料擷取失敗（已略過）：%s", ticker, e)
        logger.info("批次下載完成：%d/%d 檔股票有效。", len(result), len(tickers))
        return result
    except Exception as e:
        logger.warning("批次下載歷史資料失敗，回退至個別呼叫：%s", e)
        return {}


def prime_signals_cache_batch(
    ticker_hist_map: dict,
    max_workers: int = SCAN_THREAD_POOL_SIZE,
) -> int:
    """
    從批次下載的歷史資料預熱訊號 L1+L2 快取。
    跳過已在 L1 快取中的 ticker。
    回傳成功預熱的股票數量。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _prime_one(ticker: str, hist) -> bool:
        if _signals_cache.get(ticker) is not None:
            logger.debug("%s 訊號已在 L1 快取，略過預熱。", ticker)
            return False
        result = _fetch_signals_from_yf(ticker, pre_fetched_hist=hist)
        _signals_cache[ticker] = result
        if not _is_error_dict(result):
            _disk_set(f"{DISK_KEY_SIGNALS}:{ticker}", result, DISK_SIGNALS_TTL)
        return True

    primed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_prime_one, ticker, hist): ticker
            for ticker, hist in ticker_hist_map.items()
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                if future.result():
                    primed += 1
            except Exception as e:
                logger.warning("預熱 %s 訊號快取失敗：%s", ticker, e)
    logger.info("訊號快取預熱完成：%d/%d 檔股票。", primed, len(ticker_hist_map))
    return primed


def prewarm_signals_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, dict | None]:
    """
    並行預熱多檔股票的技術訊號快取。
    已在 L1/L2 快取中的 ticker 不會重複呼叫 yfinance。
    回傳 {ticker: signals_dict} 對照表。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_technical_signals, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.error("預熱 %s 訊號失敗：%s", ticker, exc, exc_info=True)
                results[ticker] = None
    return results


# ===========================================================================
# 股價歷史（Price History）
# ===========================================================================


def _extract_price_history(hist) -> list[dict]:
    """從 yfinance history DataFrame 中提取收盤價列表（共用 helper）。"""
    result = []
    for idx, row in hist.iterrows():
        date_str = (
            idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        )
        result.append({"date": date_str, "close": round(row["Close"], 2)})
    return result


def _piggyback_price_history(ticker: str, hist) -> None:
    """將 signals 取得的歷史資料順便寫入 price_history 快取（避免重複 yfinance 呼叫）。"""
    try:
        price_history = _extract_price_history(hist)
        _price_history_cache[ticker] = price_history
        _disk_set(
            f"{DISK_KEY_PRICE_HISTORY}:{ticker}", price_history, DISK_PRICE_HISTORY_TTL
        )
        logger.debug(
            "%s 已 piggyback 寫入 price_history 快取（%d 筆）。",
            ticker,
            len(price_history),
        )
    except Exception as e:
        logger.debug("%s piggyback price_history 失敗（非致命）：%s", ticker, e)


def _fetch_price_history_from_yf(ticker: str) -> list[dict]:
    """獨立 fetcher — 僅在 L1 + L2 皆未命中時才呼叫。"""
    try:
        _stock, hist = _yf_history(ticker, YFINANCE_HISTORY_PERIOD)
        if hist.empty:
            return []
        return _extract_price_history(hist)
    except Exception as e:
        logger.error("無法取得 %s 股價歷史：%s", ticker, e, exc_info=True)
        return []


def get_price_history(ticker: str) -> list[dict] | None:
    """
    取得股價收盤價歷史（1 年）。
    通常由 signals 的 piggyback 預先填充快取，幾乎不需額外 yfinance 呼叫。
    """
    return _cached_fetch(
        _price_history_cache,
        ticker,
        DISK_KEY_PRICE_HISTORY,
        DISK_PRICE_HISTORY_TTL,
        _fetch_price_history_from_yf,
    )


def get_benchmark_close_history(
    ticker: str,
    start: date,
    end: date,
) -> object:
    """
    取得指定基準指數在 [start, end] 日期範圍內的每日收盤價序列。

    回傳 pandas Series（index: DatetimeIndex, values: float），
    僅包含有交易的日期。呼叫端可使用 .asof() 處理市場休日。
    失敗或無資料時回傳 None。
    """
    try:
        _rate_limiter.wait()
        hist = yf.Ticker(ticker, session=_get_session()).history(
            start=start,
            end=end + timedelta(days=1),
            auto_adjust=True,
        )
        if hist.empty:
            return None
        return hist["Close"]
    except Exception as exc:
        logger.warning(
            "無法取得基準指數 %s 歷史資料（%s～%s）：%s", ticker, start, end, exc
        )
        return None


# ===========================================================================
# 護城河趨勢（毛利率 YoY）
# ===========================================================================


def _safe_loc(df, row_labels: list[str], col) -> float | None:
    """Try multiple row labels and return the first non-null value."""
    import math

    for label in row_labels:
        try:
            val = df.loc[label, col]
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                return float(val)
        except KeyError:
            continue
    return None


def _fetch_moat_from_yf(ticker: str) -> dict:
    """實際從 yfinance 分析護城河趨勢（供 _cached_fetch 使用）。"""
    try:
        financials = _yf_quarterly_financials(ticker)

        if financials is None or financials.empty:
            logger.warning("%s 無法取得季報資料。", ticker)
            return {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
            }

        columns = financials.columns.tolist()

        if len(columns) < 2:
            logger.warning("%s 季報資料不足（%d 季），無法分析。", ticker, len(columns))
            return {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
            }

        _gross_profit_labels = ["Gross Profit"]
        _operating_profit_labels = ["Operating Profit"]
        _revenue_labels = ["Total Revenue", "Operating Revenue", "Revenue", "Net Sales"]

        def _get_gross_margin(col) -> tuple[float | None, str]:
            """Return (margin_pct, margin_type) where margin_type is 'gross' or 'operating'."""
            gross_profit = _safe_loc(financials, _gross_profit_labels, col)
            margin_type = "gross"
            if gross_profit is None:
                gross_profit = _safe_loc(financials, _operating_profit_labels, col)
                margin_type = "operating"
            revenue = _safe_loc(financials, _revenue_labels, col)
            if gross_profit is not None and revenue and revenue != 0:
                return round(float(gross_profit) / float(revenue) * 100, 2), margin_type
            return None, margin_type

        def _quarter_label(col) -> str:
            if hasattr(col, "month"):
                q = (col.month - 1) // 3 + 1
                return f"{col.year}Q{q}"
            return str(col)[:7]

        # --- 5 季毛利率走勢（防呆：取實際可用筆數與 5 取小）---
        quarters_to_fetch = min(len(columns), MARGIN_TREND_QUARTERS)
        margin_trend: list[dict] = []
        for col in columns[:quarters_to_fetch]:
            gm, _ = _get_gross_margin(col)
            margin_trend.append({"date": _quarter_label(col), "value": gm})
        margin_trend.reverse()  # 最舊在左，最新在右（圖表用）

        # --- YoY 比較 ---
        latest_col = columns[0]
        current_margin, margin_type = _get_gross_margin(latest_col)

        # 優先拿第 5 季（去年同期），不足則拿最舊一季
        if len(columns) >= MARGIN_TREND_QUARTERS:
            yoy_col = columns[MARGIN_TREND_QUARTERS - 1]
        else:
            yoy_col = columns[-1]
        previous_margin, _ = _get_gross_margin(yoy_col)

        # 使用 domain 層的純判定函式
        moat_status, change = determine_moat_status(current_margin, previous_margin)

        if moat_status == MoatStatus.NOT_AVAILABLE:
            return {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
                "margin_trend": margin_trend,
            }

        result: dict = {
            "ticker": ticker,
            "current_quarter": str(latest_col.date())
            if hasattr(latest_col, "date")
            else str(latest_col),
            "yoy_quarter": str(yoy_col.date())
            if hasattr(yoy_col, "date")
            else str(yoy_col),
            "current_margin": current_margin,
            "previous_margin": previous_margin,
            "change": change,
            "moat": moat_status.value,
            "margin_trend": margin_trend,
            "margin_type": margin_type,
        }

        result["details"] = build_moat_details(
            moat_status.value, current_margin, previous_margin, change
        )
        if margin_type == "operating":
            result["details"] += " (operating margin)"

        if moat_status == MoatStatus.DETERIORATING:
            logger.warning(
                "%s 護城河惡化：毛利率 %.2f%% → 去年同期 %.2f%%（下降 %.2f pp）",
                ticker,
                current_margin,
                previous_margin,
                abs(change),
            )
        else:
            logger.info(
                "%s 護城河穩健：毛利率 %.2f%% vs 去年同期 %.2f%%（%+.2f pp）",
                ticker,
                current_margin,
                previous_margin,
                change,
            )

        return result

    except Exception as e:
        logger.error("無法分析 %s 護城河：%s", ticker, e, exc_info=True)
        return {
            "ticker": ticker,
            "moat": MoatStatus.NOT_AVAILABLE.value,
            "details": "N/A failed to get new data",
        }


def _is_moat_error(result) -> bool:
    """判斷護城河結果是否為失敗回應（NOT_AVAILABLE 狀態）。"""
    return (
        isinstance(result, dict)
        and result.get("moat") == MoatStatus.NOT_AVAILABLE.value
    )


def analyze_moat_trend(ticker: str) -> dict:
    """分析護城河趨勢。結果快取 1 小時（季報不會頻繁變動）。錯誤結果不寫入 L2/磁碟。"""
    return _cached_fetch(
        _moat_cache,
        ticker,
        DISK_KEY_MOAT,
        DISK_MOAT_TTL,
        _fetch_moat_from_yf,
        is_error=_is_moat_error,
    )


def prewarm_moat_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, dict | None]:
    """
    並行預熱多檔股票的護城河快取。
    已在 L1/L2 快取中的 ticker 不會重複呼叫 yfinance。
    回傳 {ticker: moat_dict} 對照表。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_moat_trend, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.error("預熱 %s 護城河失敗：%s", ticker, exc, exc_info=True)
                results[ticker] = None
    return results


# ===========================================================================
# 市場情緒分析
# ===========================================================================


def analyze_market_sentiment(ticker_list: list[str]) -> dict:
    """
    分析風向球股票的整體市場情緒（5 階段）。
    接受動態的 ticker_list，計算跌破 60MA 的比例。
    """
    if not ticker_list:
        return {
            "status": MarketSentiment.BULLISH.value,
            "details": t("market.no_trend_stocks", lang=DEFAULT_LANGUAGE),
            "below_60ma_pct": 0.0,
        }

    try:
        below_count = 0
        valid_count = 0

        for ticker in ticker_list:
            signals = get_technical_signals(ticker)
            if signals and "error" not in signals:
                valid_count += 1
                price = signals.get("price")
                ma60 = signals.get("ma60")
                if price is not None and ma60 is not None and price < ma60:
                    below_count += 1

        sentiment, pct = determine_market_sentiment(below_count, valid_count)

        if sentiment in _BEARISH_TIERS:
            logger.warning(
                "市場情緒：%s — %.1f%% 的風向球跌破 60MA（%d/%d）",
                sentiment.value,
                pct,
                below_count,
                valid_count,
            )
        else:
            logger.info(
                "市場情緒：%s — %.1f%% 的風向球跌破 60MA（%d/%d）",
                sentiment.value,
                pct,
                below_count,
                valid_count,
            )

        detail_key = f"market.{sentiment.value.lower()}_details"
        return {
            "status": sentiment.value,
            "details": t(
                detail_key,
                lang=DEFAULT_LANGUAGE,
                below=below_count,
                total=valid_count,
            ),
            "below_60ma_pct": pct,
        }

    except Exception as e:
        logger.error("市場情緒分析失敗：%s", e, exc_info=True)
        return {
            "status": MarketSentiment.BULLISH.value,
            "details": t("market.fallback_optimistic", lang=DEFAULT_LANGUAGE),
            "below_60ma_pct": 0.0,
        }


# ===========================================================================
# 財報日曆 (Earnings Calendar)
# ===========================================================================


def _fetch_earnings_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得財報日期（供 _cached_fetch 使用）。"""
    try:
        cal = _yf_calendar(ticker)

        result: dict = {"ticker": ticker}

        if cal is not None:
            if isinstance(cal, dict):
                earnings_dates = cal.get("Earnings Date", [])
                if earnings_dates:
                    next_date = earnings_dates[0]
                    result["earnings_date"] = (
                        next_date.isoformat()[:10]
                        if hasattr(next_date, "isoformat")
                        else str(next_date)[:10]
                    )
            else:
                if "Earnings Date" in cal.index:
                    val = cal.loc["Earnings Date"].iloc[0]
                    result["earnings_date"] = (
                        val.isoformat()[:10]
                        if hasattr(val, "isoformat")
                        else str(val)[:10]
                    )

        if "earnings_date" not in result:
            result["earnings_date"] = None

        return result

    except Exception as e:
        logger.debug("無法取得 %s 財報日期：%s", ticker, e)
        return {"ticker": ticker, "earnings_date": None}


def get_earnings_date(ticker: str) -> dict:
    """取得下次財報日期。結果快取 24 小時。"""
    return _cached_fetch(
        _earnings_cache,
        ticker,
        DISK_KEY_EARNINGS,
        DISK_EARNINGS_TTL,
        _fetch_earnings_from_yf,
    )


# ===========================================================================
# 股息資訊 (Dividend Info)
# ===========================================================================


def _fetch_dividend_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得股息資訊（供 _cached_fetch 使用）。"""
    try:
        info, dividends = _yf_dividend_data(ticker)

        dividend_yield = info.get("dividendYield")
        ex_date_raw = info.get("exDividendDate")

        ex_dividend_date = None
        if ex_date_raw:
            try:
                if isinstance(ex_date_raw, (int, float)):
                    ex_dividend_date = datetime.fromtimestamp(
                        ex_date_raw, tz=UTC
                    ).strftime("%Y-%m-%d")
                else:
                    ex_dividend_date = str(ex_date_raw)[:10]
            except Exception:
                ex_dividend_date = str(ex_date_raw)[:10]

        # Compute actual YTD dividend per share from payment history (ex-dividend dates).
        # Uses real payments rather than yield-based proration for accuracy.
        ytd_dividend_per_share: float | None = None
        try:
            if dividends is not None and not dividends.empty:
                current_year = datetime.now(tz=UTC).year
                ytd_divs = dividends[dividends.index.year == current_year]
                ytd_dividend_per_share = (
                    round(float(ytd_divs.sum()), 6) if not ytd_divs.empty else 0.0
                )
            else:
                ytd_dividend_per_share = 0.0
        except Exception as e:
            logger.debug("無法取得 %s 年初至今股息歷史：%s", ticker, e)

        return {
            "ticker": ticker,
            "dividend_yield": round(dividend_yield * 100, 2)
            if dividend_yield
            else None,
            "ex_dividend_date": ex_dividend_date,
            "ytd_dividend_per_share": ytd_dividend_per_share,
        }

    except Exception as e:
        logger.debug("無法取得 %s 股息資訊：%s", ticker, e)
        return {
            "ticker": ticker,
            "dividend_yield": None,
            "ex_dividend_date": None,
            "ytd_dividend_per_share": None,
        }


def get_dividend_info(ticker: str) -> dict:
    """取得股息資訊。結果快取避免重複呼叫 yfinance。"""
    result = _cached_fetch(
        _dividend_cache,
        ticker,
        DISK_KEY_DIVIDEND,
        DISK_DIVIDEND_TTL,
        _fetch_dividend_from_yf,
        is_error=_is_dividend_error,
    )
    # Evict and re-fetch stale cache entries that predate the ytd_dividend_per_share field.
    if isinstance(result, dict) and "ytd_dividend_per_share" not in result:
        logger.debug(
            "%s 股息快取過期（缺少 ytd_dividend_per_share），清除並重新取得。", ticker
        )
        _dividend_cache.pop(ticker, None)
        _disk_cache.delete(f"{DISK_KEY_DIVIDEND}:{ticker}")
        result = _fetch_dividend_from_yf(ticker)
        _dividend_cache[ticker] = result
        _disk_set(f"{DISK_KEY_DIVIDEND}:{ticker}", result, DISK_DIVIDEND_TTL)
    return result


# ===========================================================================
# 外匯匯率（Forex Rates）
# ===========================================================================


def _fetch_forex_rate(pair_key: str) -> float:
    """
    從 yfinance 取得單一匯率（供 _cached_fetch 使用）。
    pair_key 格式為 "DISPLAY_CURRENCY:HOLDING_CURRENCY"，例如 "USD:TWD"。
    回傳值為：1 單位 holding_currency = ? 單位 display_currency 的匯率。
    """
    try:
        display_cur, holding_cur = pair_key.split(":")
        if display_cur == holding_cur:
            return 1.0

        # yfinance 使用 {FROM}{TO}=X 格式，回傳 1 FROM = ? TO
        # 我們要的是 1 holding_cur = ? display_cur
        # 所以用 {HOLDING}{DISPLAY}=X
        yf_ticker = f"{holding_cur}{display_cur}=X"
        hist = _yf_history_short(yf_ticker, "5d")

        if hist is not None and not hist.empty:
            rate = float(hist["Close"].dropna().iloc[-1])
            logger.info("匯率 %s → %s = %.4f", holding_cur, display_cur, rate)
            return rate

        # 嘗試反向查詢
        yf_ticker_rev = f"{display_cur}{holding_cur}=X"
        hist_rev = _yf_history_short(yf_ticker_rev, "5d")

        if hist_rev is not None and not hist_rev.empty:
            rev_rate = float(hist_rev["Close"].dropna().iloc[-1])
            rate = 1.0 / rev_rate if rev_rate > 0 else 1.0
            logger.info(
                "匯率 %s → %s = %.4f（反向查詢）", holding_cur, display_cur, rate
            )
            return rate

        logger.warning("無法取得匯率 %s → %s，使用 1.0", holding_cur, display_cur)
        return 1.0

    except Exception as e:
        logger.warning("取得匯率失敗（%s）：%s，使用 1.0", pair_key, e)
        return 1.0


def get_exchange_rate(display_currency: str, holding_currency: str) -> float:
    """
    取得匯率：1 單位 holding_currency = ? 單位 display_currency。
    結果透過 L1 + L2 快取。
    """
    if display_currency == holding_currency:
        return 1.0
    pair_key = f"{display_currency}:{holding_currency}"
    return _cached_fetch(
        _forex_cache, pair_key, DISK_KEY_FOREX, DISK_FOREX_TTL, _fetch_forex_rate
    )


def get_exchange_rates(
    display_currency: str, holding_currencies: list[str]
) -> dict[str, float]:
    """
    批次取得匯率：各 holding_currency → display_currency。
    回傳 dict[holding_currency, rate]，rate 表示 1 單位 holding = ? 單位 display。
    """
    rates: dict[str, float] = {}
    for cur in set(holding_currencies):
        rates[cur] = get_exchange_rate(display_currency, cur)
    return rates


# ---------------------------------------------------------------------------
# Forex History (for Currency Exposure Monitor)
# ---------------------------------------------------------------------------


def _fetch_forex_history(pair_key: str) -> list[dict]:
    """
    從 yfinance 取得匯率歷史（供 _cached_fetch 使用）。
    pair_key 格式為 "BASE:QUOTE"，例如 "USD:TWD"。
    回傳 [{"date": "2026-02-05", "close": 32.15}, ...] 按日期升序。
    """
    try:
        base, quote = pair_key.split(":")
        if base == quote:
            return []

        yf_ticker = f"{base}{quote}=X"
        hist = _yf_history_short(yf_ticker, FX_HISTORY_PERIOD)

        if hist is not None and not hist.empty:
            return [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(float(row["Close"]), 4),
                }
                for idx, row in hist.iterrows()
                if not _is_nan(row.get("Close"))
            ]

        # 嘗試反向查詢
        yf_ticker_rev = f"{quote}{base}=X"
        hist_rev = _yf_history_short(yf_ticker_rev, FX_HISTORY_PERIOD)

        if hist_rev is not None and not hist_rev.empty:
            return [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(1.0 / float(row["Close"]), 4),
                }
                for idx, row in hist_rev.iterrows()
                if not _is_nan(row.get("Close")) and float(row["Close"]) > 0
            ]

        logger.warning("無法取得匯率歷史 %s/%s", base, quote)
        return []

    except Exception as e:
        logger.warning("取得匯率歷史失敗（%s）：%s", pair_key, e)
        return []


def get_forex_history(base: str, quote: str) -> list[dict]:
    """
    取得匯率歷史：1 base = ? quote 的每日收盤價。
    回傳 [{"date": "2026-02-05", "close": 32.15}, ...]。
    結果透過 L1 + L2 快取。
    """
    if base == quote:
        return []
    pair_key = f"{base}:{quote}"
    result = _cached_fetch(
        _forex_history_cache,
        pair_key,
        DISK_KEY_FOREX_HISTORY,
        DISK_FOREX_HISTORY_TTL,
        _fetch_forex_history,
    )
    return result if result else []


def _fetch_forex_history_long(pair_key: str) -> list[dict]:
    """
    從 yfinance 取得 3 個月匯率歷史（供 _cached_fetch 使用）。
    pair_key 格式同 _fetch_forex_history。
    """
    try:
        base, quote = pair_key.split(":")
        if base == quote:
            return []

        yf_ticker = f"{base}{quote}=X"
        hist = _yf_history_short(yf_ticker, FX_LONG_TERM_PERIOD)

        if hist is not None and not hist.empty:
            return [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(float(row["Close"]), 4),
                }
                for idx, row in hist.iterrows()
                if not _is_nan(row.get("Close"))
            ]

        # 嘗試反向查詢
        yf_ticker_rev = f"{quote}{base}=X"
        hist_rev = _yf_history_short(yf_ticker_rev, FX_LONG_TERM_PERIOD)

        if hist_rev is not None and not hist_rev.empty:
            return [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "close": round(1.0 / float(row["Close"]), 4),
                }
                for idx, row in hist_rev.iterrows()
                if not _is_nan(row.get("Close")) and float(row["Close"]) > 0
            ]

        logger.warning("無法取得長期匯率歷史 %s/%s", base, quote)
        return []

    except Exception as e:
        logger.warning("取得長期匯率歷史失敗（%s）：%s", pair_key, e)
        return []


def get_forex_history_long(base: str, quote: str) -> list[dict]:
    """
    取得 3 個月匯率歷史：1 base = ? quote 的每日收盤價。
    回傳 [{"date": "2025-11-15", "close": 31.80}, ...]。
    結果透過 L1 + L2 快取（L1: 2hr, L2: 4hr）。
    """
    if base == quote:
        return []
    pair_key = f"{base}:{quote}"
    result = _cached_fetch(
        _forex_history_long_cache,
        pair_key,
        DISK_KEY_FOREX_HISTORY_LONG,
        DISK_FOREX_HISTORY_LONG_TTL,
        _fetch_forex_history_long,
    )
    return result if result else []


def _is_nan(val) -> bool:
    """安全判斷 NaN（支援 None / float）。"""
    if val is None:
        return True
    try:
        import math

        return math.isnan(float(val))
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# ETF Holdings (for X-Ray portfolio overlap analysis)
# ---------------------------------------------------------------------------


def _fetch_etf_top_holdings(ticker: str) -> list[dict] | None:
    """
    從 yfinance 取得 ETF 前 N 大成分股。
    回傳 [{"symbol": "AAPL", "name": "Apple Inc.", "weight": 0.072}, ...] 或 None。
    非 ETF 標的會回傳 None。
    """
    _rate_limiter.wait()
    try:
        t = _yf_ticker_obj(ticker)
        fd = t.funds_data
        if fd is None:
            return None
        top = fd.top_holdings
        if top is None or top.empty:
            return None

        cols = list(top.columns)
        logger.debug(
            "%s top_holdings columns=%s, index=%s", ticker, cols, top.index.name
        )

        result = []
        for symbol, row in top.head(ETF_TOP_N).iterrows():
            # yfinance 欄位名稱可能隨版本不同：
            # "Holding Percent" (常見) / "% Assets" (舊版)
            weight = row.get("Holding Percent", row.get("% Assets"))
            if weight is None or weight == 0:
                continue
            name = row.get("Name", row.get("Holding Name", ""))
            result.append(
                {
                    "symbol": str(symbol).strip().upper(),
                    "name": str(name) if name else "",
                    "weight": float(weight),
                }
            )
        logger.info("%s ETF 成分股取得 %d 筆（前 %d）", ticker, len(result), ETF_TOP_N)
        return result if result else None
    except Exception as e:
        logger.debug("%s 非 ETF 或取得成分股失敗：%s", ticker, e)
        return None


_ETF_NOT_FOUND_SENTINEL: list[dict] = []  # 空 list 作為「非 ETF」的快取標記
_BETA_NOT_AVAILABLE: float = -999.0  # 哨兵值：yfinance 無提供 Beta 時的快取標記


def get_etf_top_holdings(ticker: str) -> list[dict] | None:
    """
    取得 ETF 前 N 大成分股（含 L1 + L2 快取）。
    非 ETF 標的回傳 None。使用空 list 哨兵避免反覆呼叫 yfinance。
    """

    def _fetch_with_sentinel(t: str) -> list[dict]:
        result = _fetch_etf_top_holdings(t)
        return result if result else _ETF_NOT_FOUND_SENTINEL

    data = _cached_fetch(
        _etf_holdings_cache,
        ticker,
        DISK_KEY_ETF_HOLDINGS,
        DISK_ETF_HOLDINGS_TTL,
        _fetch_with_sentinel,
    )
    return data if data else None


def prewarm_etf_holdings_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, list[dict] | None]:
    """
    並行預熱多檔 ETF 的成分股快取。
    回傳 {ticker: holdings_list_or_None} 對照表。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, list[dict] | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_etf_top_holdings, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.error("預熱 %s ETF 成分股失敗：%s", ticker, exc, exc_info=True)
                results[ticker] = None
    return results


# ===========================================================================
# ETF 行業板塊權重（Sector Weightings）
# ===========================================================================

_ETF_SECTOR_WEIGHTS_NOT_FOUND: dict = {}  # 空 dict 哨兵值：非 ETF 或無資料時的快取標記

# yfinance funds_data.sector_weightings 使用 snake_case 鍵；此對照表轉換為 GICS 標準名稱。
# 未收錄的鍵直接用 .title() 處理（如 "other" → "Other"）。
_ETF_SECTOR_KEY_MAP: dict[str, str] = {
    "technology": "Technology",
    "consumer_cyclical": "Consumer Cyclical",
    "financial_services": "Financial Services",
    "realestate": "Real Estate",
    "consumer_defensive": "Consumer Defensive",
    "healthcare": "Healthcare",
    "utilities": "Utilities",
    "communication_services": "Communication Services",
    "energy": "Energy",
    "industrials": "Industrials",
    "basic_materials": "Basic Materials",
}


def _fetch_etf_sector_weights(ticker: str) -> dict[str, float] | None:
    """
    從 yfinance funds_data.sector_weightings 取得 ETF 的行業板塊權重分佈。
    回傳 {"Technology": 0.32, "Healthcare": 0.14, ...} 或 None。
    涵蓋 100% ETF 資產，比分析成分股更準確。
    非 ETF 標的或無資料時回傳 None。
    """
    _rate_limiter.wait()
    try:
        t = _yf_ticker_obj(ticker)
        fd = t.funds_data
        if fd is None:
            return None
        weights = fd.sector_weightings
        if not weights:
            return None
        # yfinance 回傳 list[dict] 或 dict，視版本而定
        # list[dict] 格式：[{"realestate": 0.01, "consumer_cyclical": 0.13, ...}]
        # dict 格式：{"realestate": 0.01, ...}
        if isinstance(weights, list):
            if not weights:
                return None
            merged: dict[str, float] = {}
            for item in weights:
                if isinstance(item, dict):
                    merged.update(item)
            weights = merged
        if not isinstance(weights, dict) or not weights:
            return None

        result: dict[str, float] = {}
        for raw_key, weight in weights.items():
            if not isinstance(weight, (int, float)) or weight <= 0:
                continue
            normalized = _ETF_SECTOR_KEY_MAP.get(
                str(raw_key).lower(), str(raw_key).title()
            )
            result[normalized] = result.get(normalized, 0.0) + float(weight)

        if not result:
            return None
        logger.info("%s ETF 行業板塊權重取得 %d 個板塊", ticker, len(result))
        return result
    except Exception as e:
        logger.debug("%s 非 ETF 或取得行業板塊權重失敗：%s", ticker, e)
        return None


def get_etf_sector_weights(ticker: str) -> dict[str, float] | None:
    """
    取得 ETF 行業板塊權重分佈（含 L1 + L2 快取）。
    回傳 {"Technology": 0.32, ...} 或 None（非 ETF 或無資料）。
    使用空 dict 哨兵避免反覆呼叫 yfinance。
    """

    def _fetch_with_sentinel(t: str) -> dict[str, float]:
        result = _fetch_etf_sector_weights(t)
        return result if result else _ETF_SECTOR_WEIGHTS_NOT_FOUND

    data = _cached_fetch(
        _etf_sector_weights_cache,
        ticker,
        DISK_KEY_ETF_SECTOR_WEIGHTS,
        DISK_ETF_SECTOR_WEIGHTS_TTL,
        _fetch_with_sentinel,
    )
    return data if data else None


def prewarm_etf_sector_weights_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, dict[str, float] | None]:
    """
    並行預熱多檔 ETF 的行業板塊權重快取。
    非 ETF 標的會快速命中哨兵快取，不造成額外 yfinance 呼叫。
    回傳 {ticker: weights_or_None} 對照表。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, dict[str, float] | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_etf_sector_weights, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.error(
                    "預熱 %s ETF 行業板塊權重失敗：%s", ticker, exc, exc_info=True
                )
                results[ticker] = None
    return results


# ===========================================================================
# 恐懼與貪婪指數 (Fear & Greed Index)
# ===========================================================================


def get_vix_data() -> dict:
    """
    從 yfinance 取得 VIX 指數資料。
    回傳 {"value": float, "change_1d": float, "level": str, "fetched_at": str}。
    失敗時回傳 {"value": None, "level": "N/A", ...}。
    """
    try:
        hist = _yf_history_short(VIX_TICKER, VIX_HISTORY_PERIOD)

        if hist is None or hist.empty:
            logger.warning("VIX 資料為空。")
            return {
                "value": None,
                "change_1d": None,
                "level": FearGreedLevel.NOT_AVAILABLE.value,
                "fetched_at": datetime.now(UTC).isoformat(),
            }

        closes = hist["Close"].dropna().tolist()
        if not closes:
            return {
                "value": None,
                "change_1d": None,
                "level": FearGreedLevel.NOT_AVAILABLE.value,
                "fetched_at": datetime.now(UTC).isoformat(),
            }

        current_vix = round(float(closes[-1]), 2)
        change_1d = (
            round(float(closes[-1] - closes[-2]), 2) if len(closes) >= 2 else None
        )

        vix_level = classify_vix(current_vix)

        logger.info(
            "VIX = %.2f（等級：%s，日變動：%s）",
            current_vix,
            vix_level.value,
            change_1d,
        )

        return {
            "value": current_vix,
            "change_1d": change_1d,
            "level": vix_level.value,
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error("取得 VIX 資料失敗：%s", e, exc_info=True)
        return {
            "value": None,
            "change_1d": None,
            "level": FearGreedLevel.NOT_AVAILABLE.value,
            "fetched_at": datetime.now(UTC).isoformat(),
        }


def get_cnn_fear_greed() -> dict | None:
    """
    從 CNN Fear & Greed Index API 取得市場恐懼貪婪分數。
    回傳 {"score": int, "label": str, "level": str, "fetched_at": str} 或 None。
    此為非官方 API，失敗時靜默回傳 None（graceful degradation）。
    """
    try:
        session = _get_session()
        resp = session.get(CNN_FG_API_URL, timeout=CNN_FG_REQUEST_TIMEOUT)
        resp.raise_for_status()

        data = resp.json()

        # CNN API 回傳結構：{"fear_and_greed": {"score": 42, "rating": "Fear", ...}}
        fg_data = data.get("fear_and_greed", {})
        score_raw = fg_data.get("score")
        label = fg_data.get("rating", "")

        if score_raw is None:
            logger.warning("CNN Fear & Greed API 回傳無 score 欄位。")
            return None

        score = round(float(score_raw))
        from domain.analysis import classify_cnn_fear_greed

        level = classify_cnn_fear_greed(score)

        logger.info("CNN Fear & Greed = %d（%s，等級：%s）", score, label, level.value)

        return {
            "score": score,
            "label": label,
            "level": level.value,
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.warning("CNN Fear & Greed API 取得失敗（非致命）：%s", e)
        return None


def _fetch_fear_greed(_key: str) -> dict:
    """
    綜合 VIX 與 CNN Fear & Greed 資料（供 _cached_fetch 使用）。
    _key 固定為 "composite"。
    """
    vix_data = get_vix_data()
    cnn_data = get_cnn_fear_greed()

    vix_value = vix_data.get("value")
    cnn_score = cnn_data.get("score") if cnn_data else None

    level, composite_score = compute_composite_fear_greed(vix_value, cnn_score)

    return {
        "composite_score": composite_score,
        "composite_level": level.value,
        "vix": vix_data,
        "cnn": cnn_data,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def _is_fear_greed_error(result) -> bool:
    """判斷 Fear & Greed 結果是否為失敗回應。"""
    return (
        isinstance(result, dict)
        and result.get("composite_level") == FearGreedLevel.NOT_AVAILABLE.value
    )


def get_fear_greed_index() -> dict:
    """
    取得恐懼與貪婪指數（VIX + CNN 綜合）。
    結果透過 L1 + L2 快取（L1: 30 分鐘，L2: 2 小時）。
    錯誤結果僅寫入 L1，不寫入 L2。
    """
    return _cached_fetch(
        _fear_greed_cache,
        "composite",
        DISK_KEY_FEAR_GREED,
        DISK_FEAR_GREED_TTL,
        _fetch_fear_greed,
        is_error=_is_fear_greed_error,
    )


def get_jp_volatility_index() -> dict | None:
    """
    Fetch Nikkei VI as JP market fear indicator.
    Returns {"value": float, "level": str, "source": "Nikkei VI"} or None on failure.
    """
    try:
        hist = _yf_history_short(NIKKEI_VI_TICKER, VIX_HISTORY_PERIOD)

        if hist is None or hist.empty:
            logger.warning("Nikkei VI 資料為空。")
            return None

        closes = hist["Close"].dropna().tolist()
        if not closes:
            return None

        current = float(closes[-1])

        # Map to fear/greed level using JP thresholds (similar to VIX mapping)
        if current > NIKKEI_VI_EXTREME_FEAR:
            level = FearGreedLevel.EXTREME_FEAR.value
        elif current > NIKKEI_VI_FEAR:
            level = FearGreedLevel.FEAR.value
        elif current > NIKKEI_VI_NEUTRAL_LOW:
            level = FearGreedLevel.NEUTRAL.value
        elif current > NIKKEI_VI_GREED:
            level = FearGreedLevel.GREED.value
        else:
            level = FearGreedLevel.EXTREME_GREED.value

        logger.info("Nikkei VI = %.2f（等級：%s）", current, level)
        return {"value": round(current, 2), "level": level, "source": "Nikkei VI"}

    except Exception as e:
        logger.warning("Nikkei VI 取得失敗：%s", e)
        return None


def get_tw_volatility_index() -> dict | None:
    """
    Calculate TW market fear indicator from ^TWII realized volatility.
    Fetches 1 month of TAIEX daily closes and computes annualized realized vol.
    Returns {"value": float, "level": str, "source": "TAIEX Realized Vol"} or None on failure.
    """
    try:
        hist = _yf_history_short(TWII_TICKER, "1mo")

        if hist is None or hist.empty:
            logger.warning("TAIEX ^TWII 資料為空。")
            return None

        closes = hist["Close"].dropna()
        if len(closes) < 5:
            logger.warning("TAIEX ^TWII 資料不足（%d 筆），需至少 5 筆。", len(closes))
            return None

        returns = (closes / closes.shift(1)).apply(math.log).dropna()
        annualized_vol = float(returns.std() * math.sqrt(252) * 100)

        if annualized_vol > TWII_VOL_EXTREME_FEAR:
            level = FearGreedLevel.EXTREME_FEAR.value
        elif annualized_vol > TWII_VOL_FEAR:
            level = FearGreedLevel.FEAR.value
        elif annualized_vol > TWII_VOL_NEUTRAL_LOW:
            level = FearGreedLevel.NEUTRAL.value
        elif annualized_vol > TWII_VOL_GREED:
            level = FearGreedLevel.GREED.value
        else:
            level = FearGreedLevel.EXTREME_GREED.value

        logger.info(
            "TAIEX realized vol = %.2f%%（等級：%s，source=twii, market=TW）",
            annualized_vol,
            level,
        )
        return {
            "value": round(annualized_vol, 2),
            "level": level,
            "source": "TAIEX Realized Vol",
        }

    except Exception as e:
        logger.warning("TAIEX realized vol 取得失敗：%s", e)
        return None


# ===========================================================================
# 股票 Beta（壓力測試用）
# ===========================================================================


def _fetch_beta_from_yf(ticker: str) -> float:
    """
    從 yfinance info 取得 Beta 值（供 _cached_fetch 使用）。
    回傳實際 Beta 或 _BETA_NOT_AVAILABLE 哨兵值（永不回傳 None，確保可快取）。
    """
    try:
        info = _yf_info(ticker)
        beta = info.get("beta")
        if beta is not None:
            beta = round(float(beta), 2)
            logger.info("%s Beta = %.2f", ticker, beta)
            return beta
        else:
            logger.debug("%s yfinance 未提供 Beta 值，使用哨兵值。", ticker)
            return _BETA_NOT_AVAILABLE
    except Exception as e:
        logger.warning("無法取得 %s Beta：%s，使用哨兵值。", ticker, e)
        return _BETA_NOT_AVAILABLE


def get_stock_beta(ticker: str) -> float | None:
    """
    取得股票 Beta 值。
    結果透過 L1 + L2 快取（L1: 24 小時，L2: 7 天）。
    回傳 None 表示 yfinance 無提供（呼叫端應使用 CATEGORY_FALLBACK_BETA）。

    內部使用哨兵值 _BETA_NOT_AVAILABLE 以確保「無 Beta」狀態可被快取，
    避免對無 Beta 的 ticker（如加密貨幣、新 IPO）反覆呼叫 yfinance。
    """
    result = _cached_fetch(
        _beta_cache,
        ticker,
        DISK_KEY_BETA,
        DISK_BETA_TTL,
        _fetch_beta_from_yf,
    )
    # 將哨兵值轉回 None 給呼叫端
    return None if result == _BETA_NOT_AVAILABLE else result


def prewarm_beta_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, float | None]:
    """
    並行預熱多檔股票的 Beta 快取。
    已在 L1/L2 快取中的 ticker 不會重複呼叫 yfinance。
    回傳 {ticker: beta_or_None} 對照表。
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, float | None] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_stock_beta, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.error("預熱 %s Beta 失敗：%s", ticker, exc, exc_info=True)
                results[ticker] = None
    return results


# ===========================================================================
# Rogue Wave (瘋狗浪) — 歷史乖離率分佈
# ===========================================================================


def _fetch_bias_distribution_from_yf(ticker: str) -> dict:
    """
    從 yfinance 取得 3 年日線歷史，計算每日乖離率分佈（供 _cached_fetch 使用）。

    回傳：
        {"historical_biases": sorted_list, "count": int, "p95": float, "fetched_at": str}
    失敗時回傳空 dict {}（graceful fallback）。
    """
    try:
        _stock, hist = _yf_history(ticker, ROGUE_WAVE_HISTORY_PERIOD)

        if hist.empty:
            logger.warning("%s 瘋狗浪：yfinance 回傳空資料。", ticker)
            return {}

        closes = hist["Close"].tolist()

        # 計算每日乖離率：每天用截至當天所有資料的 MA60
        biases: list[float] = []
        for i in range(len(closes)):
            if i + 1 < MA60_WINDOW:
                continue  # MA60 尚不可用
            window_closes = closes[i + 1 - MA60_WINDOW : i + 1]
            ma60 = sum(window_closes) / MA60_WINDOW
            bias = compute_bias(closes[i], ma60)
            if bias is None:
                continue
            biases.append(bias)

        if len(biases) < ROGUE_WAVE_MIN_HISTORY_DAYS:
            logger.warning(
                "%s 瘋狗浪：乖離率樣本不足（%d 筆，需 %d 筆）。",
                ticker,
                len(biases),
                ROGUE_WAVE_MIN_HISTORY_DAYS,
            )
            return {}

        biases.sort()
        p95_idx = int(len(biases) * 0.95)
        p95 = biases[min(p95_idx, len(biases) - 1)]

        logger.info(
            "%s 瘋狗浪分佈：%d 筆，P95=%.2f%%",
            ticker,
            len(biases),
            p95,
        )

        return {
            "historical_biases": biases,
            "count": len(biases),
            "p95": round(p95, 2),
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error("無法取得 %s 瘋狗浪分佈：%s", ticker, e, exc_info=True)
        return {}


def _is_rogue_wave_error(result) -> bool:
    """判斷瘋狗浪分佈結果是否為空（失敗）回應。"""
    return not result  # empty dict is falsy


def get_bias_distribution(ticker: str) -> dict:
    """
    取得股票 3 年歷史乖離率分佈。

    回傳 {"historical_biases": sorted_list, "count": int, "p95": float, "fetched_at": str}
    或空 dict {}（yfinance 失敗 / 資料不足時）。

    結果透過 L1 + L2 快取（L1: 24 小時，L2: 48 小時）。
    歷史偏態分佈變動緩慢，長 TTL 適合此場景。
    錯誤結果（空 dict）僅寫入 L1（短暫），不寫入 L2。
    """
    return _cached_fetch(
        _rogue_wave_cache,
        ticker,
        DISK_KEY_ROGUE_WAVE,
        DISK_ROGUE_WAVE_TTL,
        _fetch_bias_distribution_from_yf,
        is_error=_is_rogue_wave_error,
    )


# ===========================================================================
# 行業板塊（Sector）
# ===========================================================================

_SECTOR_NOT_FOUND: str = "__none__"  # 哨兵值：無法取得 sector 時的快取標記


def _fetch_sector_from_yf(ticker: str) -> str:
    """
    從 yfinance info 取得行業板塊。
    回傳行業板塊字串，或 _SECTOR_NOT_FOUND 哨兵值（確保可快取 None 狀態）。
    """
    try:
        _rate_limiter.wait()
        info = _yf_info(ticker)
        sector = info.get("sector")
        if sector:
            logger.info("%s 行業板塊 = %s", ticker, sector)
            return str(sector)
        logger.debug("%s yfinance 未提供 sector，使用哨兵值。", ticker)
        return _SECTOR_NOT_FOUND
    except Exception as e:
        logger.debug("無法取得 %s sector：%s，使用哨兵值。", ticker, e)
        return _SECTOR_NOT_FOUND


def get_ticker_sector(ticker: str) -> str | None:
    """
    取得股票行業板塊（GICS sector）。
    行業板塊極少變動，透過 L2 磁碟快取（30 天 TTL）。
    若快取未命中，會發起 yfinance 網路請求（可能耗時 10–15 秒）。

    回傳板塊名稱字串（如 "Technology"）或 None（無資料 / 非股票）。
    """
    if not ticker:
        return None

    disk_key = f"{DISK_KEY_SECTOR}:{ticker}"
    cached = _disk_get(disk_key)
    if cached is not None:
        return None if cached == _SECTOR_NOT_FOUND else cached

    result = _fetch_sector_from_yf(ticker)
    _disk_set(disk_key, result, DISK_SECTOR_TTL)
    return None if result == _SECTOR_NOT_FOUND else result


def get_ticker_sector_cached(ticker: str) -> str | None:
    """
    從磁碟快取讀取行業板塊（非阻塞版本）。
    若快取未命中，直接回傳 None — 不發起任何 yfinance 網路請求。

    專供熱路徑（如 `/rebalance` 端點）使用，避免因 yfinance 呼叫而阻塞請求。
    背景預熱（prewarm_service）負責填充快取，確保後續呼叫可命中。
    """
    if not ticker:
        return None
    cached = _disk_get(f"{DISK_KEY_SECTOR}:{ticker}")
    if cached is not None:
        return None if cached == _SECTOR_NOT_FOUND else cached
    return None


# ---------------------------------------------------------------------------
# Phase 7 — Performance Since Filing (price pair fetch with disk cache)
# ---------------------------------------------------------------------------


def fetch_price_pair(tickers: list[str], report_date: str) -> dict[str, dict]:
    """Fetch (report_date close, current close) for each ticker using yfinance.

    Uses L2 disk cache with permanent TTL for historical close prices — they are
    immutable once the market closes. Current prices are never cached (always live).
    Returns {ticker: {report_price: float|None, current_price: float|None}}.
    All failures are silently set to None (never raises).
    """
    from datetime import timedelta

    result: dict[str, dict] = {
        t: {"report_price": None, "current_price": None} for t in tickers
    }

    if not tickers:
        return result

    # Load historical (report_date) close prices — try disk cache first
    uncached_tickers: list[str] = []
    report_prices: dict[str, float | None] = {}
    for ticker in tickers:
        disk_key = f"{DISK_KEY_PRICE_PAIR}:{report_date}:{ticker}"
        cached = _disk_get(disk_key)
        if cached is not None:
            report_prices[ticker] = cached.get("report_price")
        else:
            uncached_tickers.append(ticker)

    # Batch-fetch historical prices for uncached tickers
    if uncached_tickers:
        try:
            _rate_limiter.wait()
            end_date = (
                (datetime.fromisoformat(report_date) + timedelta(days=5))
                .date()
                .isoformat()
            )
            hist = yf.download(
                uncached_tickers,
                start=report_date,
                end=end_date,
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            for ticker in uncached_tickers:
                rp: float | None = None
                try:
                    if len(uncached_tickers) == 1:
                        rp = float(hist["Close"].iloc[0]) if not hist.empty else None
                    else:
                        col = hist["Close"].get(ticker)
                        if col is not None:
                            dropped = col.dropna()
                            rp = float(dropped.iloc[0]) if not dropped.empty else None
                except Exception:
                    rp = None
                report_prices[ticker] = rp
                # Persist to disk cache permanently (historical prices are immutable)
                disk_key = f"{DISK_KEY_PRICE_PAIR}:{report_date}:{ticker}"
                _disk_set(disk_key, {"report_price": rp}, DISK_PRICE_PAIR_TTL)
        except Exception:
            # Leave all uncached tickers with None
            for ticker in uncached_tickers:
                report_prices[ticker] = None

    # Fetch current prices (never cached — always live)
    current_prices: dict[str, float | None] = {t: None for t in tickers}
    try:
        _rate_limiter.wait()
        current = yf.download(
            tickers,
            period="5d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        for ticker in tickers:
            cp: float | None = None
            try:
                if len(tickers) == 1:
                    cp = float(current["Close"].iloc[-1]) if not current.empty else None
                else:
                    col = current["Close"].get(ticker)
                    if col is not None:
                        dropped = col.dropna()
                        cp = float(dropped.iloc[-1]) if not dropped.empty else None
            except Exception:
                cp = None
            current_prices[ticker] = cp
    except Exception:
        pass  # leave all current_prices as None

    for ticker in tickers:
        result[ticker] = {
            "report_price": report_prices.get(ticker),
            "current_price": current_prices.get(ticker),
        }

    return result
