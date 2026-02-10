"""
Infrastructure — 市場資料適配器 (yfinance)。
負責外部 API 呼叫、快取管理、速率限制。
所有呼叫皆以 try/except 包裹，失敗時回傳結構化降級結果。
"""

import threading
import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

import diskcache
import yfinance as yf
from cachetools import TTLCache
from curl_cffi import requests as cffi_requests

from domain.analysis import (
    compute_bias,
    compute_moving_average,
    compute_rsi,
    compute_volume_ratio,
    determine_market_sentiment,
    determine_moat_status,
)
from application.formatters import build_moat_details, build_signal_status
from domain.constants import (
    CURL_CFFI_IMPERSONATE,
    DISK_CACHE_DIR,
    DISK_CACHE_SIZE_LIMIT,
    DISK_DIVIDEND_TTL,
    DISK_EARNINGS_TTL,
    DISK_ETF_HOLDINGS_TTL,
    DISK_FOREX_TTL,
    DISK_KEY_DIVIDEND,
    DISK_KEY_EARNINGS,
    DISK_KEY_ETF_HOLDINGS,
    DISK_KEY_FOREX,
    DISK_KEY_MOAT,
    DISK_KEY_PRICE_HISTORY,
    DISK_KEY_SIGNALS,
    DISK_MOAT_TTL,
    DISK_PRICE_HISTORY_TTL,
    DISK_SIGNALS_TTL,
    DIVIDEND_CACHE_MAXSIZE,
    DIVIDEND_CACHE_TTL,
    EARNINGS_CACHE_MAXSIZE,
    EARNINGS_CACHE_TTL,
    ETF_HOLDINGS_CACHE_MAXSIZE,
    ETF_HOLDINGS_CACHE_TTL,
    ETF_TOP_N,
    FOREX_CACHE_MAXSIZE,
    FOREX_CACHE_TTL,
    INSTITUTIONAL_HOLDERS_TOP_N,
    MA200_WINDOW,
    MA60_WINDOW,
    MARGIN_TREND_QUARTERS,
    MIN_HISTORY_DAYS_FOR_SIGNALS,
    MOAT_CACHE_MAXSIZE,
    MOAT_CACHE_TTL,
    PRICE_HISTORY_CACHE_MAXSIZE,
    PRICE_HISTORY_CACHE_TTL,
    SIGNALS_CACHE_MAXSIZE,
    SIGNALS_CACHE_TTL,
    YFINANCE_HISTORY_PERIOD,
    YFINANCE_RATE_LIMIT_CPS,
)
from domain.enums import MarketSentiment, MoatStatus
from logging_config import get_logger

logger = get_logger(__name__)


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
# L1 快取（記憶體）：避免每次頁面載入都重複呼叫 yfinance
# ---------------------------------------------------------------------------
_signals_cache: TTLCache = TTLCache(maxsize=SIGNALS_CACHE_MAXSIZE, ttl=SIGNALS_CACHE_TTL)
_moat_cache: TTLCache = TTLCache(maxsize=MOAT_CACHE_MAXSIZE, ttl=MOAT_CACHE_TTL)
_earnings_cache: TTLCache = TTLCache(maxsize=EARNINGS_CACHE_MAXSIZE, ttl=EARNINGS_CACHE_TTL)
_dividend_cache: TTLCache = TTLCache(maxsize=DIVIDEND_CACHE_MAXSIZE, ttl=DIVIDEND_CACHE_TTL)
_price_history_cache: TTLCache = TTLCache(maxsize=PRICE_HISTORY_CACHE_MAXSIZE, ttl=PRICE_HISTORY_CACHE_TTL)
_forex_cache: TTLCache = TTLCache(maxsize=FOREX_CACHE_MAXSIZE, ttl=FOREX_CACHE_TTL)
_etf_holdings_cache: TTLCache = TTLCache(maxsize=ETF_HOLDINGS_CACHE_MAXSIZE, ttl=ETF_HOLDINGS_CACHE_TTL)


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
    try:
        _disk_cache.set(key, value, expire=ttl)
    except Exception:
        pass


def _cached_fetch(
    l1_cache: TTLCache,
    ticker: str,
    disk_prefix: str,
    disk_ttl: int,
    fetcher: Callable[[str], T],
) -> T:
    """
    通用二層快取取得函式。
    L1 (記憶體) → L2 (磁碟) → fetcher (yfinance)，並回寫兩層快取。
    """
    cached = l1_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 命中 L1 快取（prefix=%s）。", ticker, disk_prefix)
        return cached

    disk_key = f"{disk_prefix}:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("%s 命中 L2 磁碟快取（prefix=%s）。", ticker, disk_prefix)
        l1_cache[ticker] = disk_cached
        return disk_cached

    logger.debug("%s L1+L2 皆未命中（prefix=%s），呼叫 fetcher...", ticker, disk_prefix)
    result = fetcher(ticker)
    l1_cache[ticker] = result
    _disk_set(disk_key, result, disk_ttl)
    return result


def _get_session() -> cffi_requests.Session:
    """建立模擬 Chrome 瀏覽器的 Session，以繞過 Yahoo Finance 的 bot 防護。"""
    return cffi_requests.Session(impersonate=CURL_CFFI_IMPERSONATE)


# ===========================================================================
# 技術面訊號
# ===========================================================================


def _fetch_signals_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得技術訊號（供 _cached_fetch 使用）。"""
    try:
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        hist = stock.history(period=YFINANCE_HISTORY_PERIOD)

        if hist.empty or len(hist) < MIN_HISTORY_DAYS_FOR_SIGNALS:
            logger.warning("%s 歷史資料不足（%d 筆），無法計算技術指標。", ticker, len(hist))
            return {"error": f"⚠️ {ticker} 歷史資料不足，無法計算技術指標。"}

        # Piggyback：將收盤價歷史寫入 price_history 快取，避免後續重複呼叫 yfinance
        _piggyback_price_history(ticker, hist)

        closes = hist["Close"].tolist()
        volumes = hist["Volume"].tolist() if "Volume" in hist.columns else []
        current_price = round(closes[-1], 2)

        # 使用 domain 層的純計算函式
        rsi = compute_rsi(closes)
        ma200 = compute_moving_average(closes, MA200_WINDOW)
        ma60 = compute_moving_average(closes, MA60_WINDOW)
        bias = compute_bias(current_price, ma60) if ma60 else None
        volume_ratio = compute_volume_ratio(volumes)

        logger.info(
            "%s 技術訊號：price=%.2f, RSI=%s, 200MA=%s, 60MA=%s, Bias=%s%%, VolRatio=%s",
            ticker, current_price, rsi, ma200, ma60, bias, volume_ratio,
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
                        elif val is None or (hasattr(val, "item") and str(val) == "NaT"):
                            holder_entry[col] = "N/A"
                        else:
                            holder_entry[col] = val if not hasattr(val, "item") else val.item()
                    institutional_holders.append(holder_entry)
                logger.debug("%s 機構持倉：取得 %d 筆", ticker, len(institutional_holders))
        except Exception as holder_err:
            logger.debug("%s 機構持倉取得失敗（非致命）：%s", ticker, holder_err)

        raw_signals = {
            "ticker": ticker,
            "price": current_price,
            "rsi": rsi,
            "ma200": ma200,
            "ma60": ma60,
            "bias": bias,
            "volume_ratio": volume_ratio,
            "institutional_holders": institutional_holders,
        }
        return {**raw_signals, "status": build_signal_status(raw_signals)}

    except Exception as e:
        logger.error("無法取得 %s 技術訊號：%s", ticker, e, exc_info=True)
        return {"error": f"⚠️ 無法取得 {ticker} 技術訊號：{e}"}


def get_technical_signals(ticker: str) -> Optional[dict]:
    """
    取得技術面訊號：RSI(14)、現價、200MA、60MA、Bias(%)、Volume Ratio。
    結果快取 5 分鐘。含 error 的結果也會快取以避免重複失敗呼叫。
    """
    return _cached_fetch(
        _signals_cache, ticker, DISK_KEY_SIGNALS, DISK_SIGNALS_TTL, _fetch_signals_from_yf
    )


# ===========================================================================
# 股價歷史（Price History）
# ===========================================================================


def _extract_price_history(hist) -> list[dict]:
    """從 yfinance history DataFrame 中提取收盤價列表（共用 helper）。"""
    result = []
    for idx, row in hist.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        result.append({"date": date_str, "close": round(row["Close"], 2)})
    return result


def _piggyback_price_history(ticker: str, hist) -> None:
    """將 signals 取得的歷史資料順便寫入 price_history 快取（避免重複 yfinance 呼叫）。"""
    try:
        price_history = _extract_price_history(hist)
        _price_history_cache[ticker] = price_history
        _disk_set(f"{DISK_KEY_PRICE_HISTORY}:{ticker}", price_history, DISK_PRICE_HISTORY_TTL)
        logger.debug("%s 已 piggyback 寫入 price_history 快取（%d 筆）。", ticker, len(price_history))
    except Exception as e:
        logger.debug("%s piggyback price_history 失敗（非致命）：%s", ticker, e)


def _fetch_price_history_from_yf(ticker: str) -> list[dict]:
    """獨立 fetcher — 僅在 L1 + L2 皆未命中時才呼叫。"""
    try:
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        hist = stock.history(period=YFINANCE_HISTORY_PERIOD)
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
        _price_history_cache, ticker,
        DISK_KEY_PRICE_HISTORY, DISK_PRICE_HISTORY_TTL,
        _fetch_price_history_from_yf,
    )


# ===========================================================================
# 護城河趨勢（毛利率 YoY）
# ===========================================================================


def _fetch_moat_from_yf(ticker: str) -> dict:
    """實際從 yfinance 分析護城河趨勢（供 _cached_fetch 使用）。"""
    try:
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        financials = stock.quarterly_financials

        if financials is None or financials.empty:
            logger.warning("%s 無法取得季報資料。", ticker)
            return {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}

        columns = financials.columns.tolist()

        if len(columns) < 2:
            logger.warning("%s 季報資料不足（%d 季），無法分析。", ticker, len(columns))
            return {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}

        def _get_gross_margin(col) -> Optional[float]:
            try:
                gross_profit = financials.loc["Gross Profit", col]
                revenue = financials.loc["Total Revenue", col]
                if revenue and revenue != 0:
                    return round(float(gross_profit) / float(revenue) * 100, 2)
            except KeyError:
                pass
            return None

        def _quarter_label(col) -> str:
            if hasattr(col, "month"):
                q = (col.month - 1) // 3 + 1
                return f"{col.year}Q{q}"
            return str(col)[:7]

        # --- 5 季毛利率走勢（防呆：取實際可用筆數與 5 取小）---
        quarters_to_fetch = min(len(columns), MARGIN_TREND_QUARTERS)
        margin_trend: list[dict] = []
        for col in columns[:quarters_to_fetch]:
            gm = _get_gross_margin(col)
            margin_trend.append({"date": _quarter_label(col), "value": gm})
        margin_trend.reverse()  # 最舊在左，最新在右（圖表用）

        # --- YoY 比較 ---
        latest_col = columns[0]
        current_margin = _get_gross_margin(latest_col)

        # 優先拿第 5 季（去年同期），不足則拿最舊一季
        if len(columns) >= MARGIN_TREND_QUARTERS:
            yoy_col = columns[MARGIN_TREND_QUARTERS - 1]
        else:
            yoy_col = columns[-1]
        previous_margin = _get_gross_margin(yoy_col)

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
            "current_quarter": str(latest_col.date()) if hasattr(latest_col, "date") else str(latest_col),
            "yoy_quarter": str(yoy_col.date()) if hasattr(yoy_col, "date") else str(yoy_col),
            "current_margin": current_margin,
            "previous_margin": previous_margin,
            "change": change,
            "moat": moat_status.value,
            "margin_trend": margin_trend,
        }

        result["details"] = build_moat_details(
            moat_status.value, current_margin, previous_margin, change
        )

        if moat_status == MoatStatus.DETERIORATING:
            logger.warning(
                "%s 護城河惡化：毛利率 %.2f%% → 去年同期 %.2f%%（下降 %.2f pp）",
                ticker, current_margin, previous_margin, abs(change),
            )
        else:
            logger.info(
                "%s 護城河穩健：毛利率 %.2f%% vs 去年同期 %.2f%%（%+.2f pp）",
                ticker, current_margin, previous_margin, change,
            )

        return result

    except Exception as e:
        logger.error("無法分析 %s 護城河：%s", ticker, e, exc_info=True)
        return {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}


def analyze_moat_trend(ticker: str) -> dict:
    """分析護城河趨勢。結果快取 1 小時（季報不會頻繁變動）。"""
    return _cached_fetch(
        _moat_cache, ticker, DISK_KEY_MOAT, DISK_MOAT_TTL, _fetch_moat_from_yf
    )


# ===========================================================================
# 市場情緒分析
# ===========================================================================


def analyze_market_sentiment(ticker_list: list[str]) -> dict:
    """
    分析風向球股票的整體市場情緒。
    接受動態的 ticker_list，計算跌破 60MA 的比例。
    """
    if not ticker_list:
        return {"status": MarketSentiment.POSITIVE.value, "details": "無風向球股票可供分析", "below_60ma_pct": 0.0}

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

        # 使用 domain 層的純判定函式
        sentiment, pct = determine_market_sentiment(below_count, valid_count)

        if sentiment == MarketSentiment.CAUTION:
            logger.warning(
                "市場情緒：CAUTION — %.1f%% 的風向球跌破 60MA（%d/%d）",
                pct, below_count, valid_count,
            )
            return {
                "status": sentiment.value,
                "details": f"多數風向球股價轉弱（{below_count}/{valid_count} 跌破 60MA）",
                "below_60ma_pct": pct,
            }

        logger.info(
            "市場情緒：POSITIVE — %.1f%% 的風向球跌破 60MA（%d/%d）",
            pct, below_count, valid_count,
        )
        return {
            "status": sentiment.value,
            "details": f"風向球整體穩健（{below_count}/{valid_count} 跌破 60MA）",
            "below_60ma_pct": pct,
        }

    except Exception as e:
        logger.error("市場情緒分析失敗：%s", e, exc_info=True)
        return {"status": MarketSentiment.POSITIVE.value, "details": "無法判斷，預設樂觀", "below_60ma_pct": 0.0}


# ===========================================================================
# 財報日曆 (Earnings Calendar)
# ===========================================================================


def _fetch_earnings_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得財報日期（供 _cached_fetch 使用）。"""
    try:
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        cal = stock.calendar

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
        _earnings_cache, ticker, DISK_KEY_EARNINGS, DISK_EARNINGS_TTL, _fetch_earnings_from_yf
    )


# ===========================================================================
# 股息資訊 (Dividend Info)
# ===========================================================================


def _fetch_dividend_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得股息資訊（供 _cached_fetch 使用）。"""
    try:
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        info = stock.info or {}

        dividend_yield = info.get("dividendYield")
        ex_date_raw = info.get("exDividendDate")

        ex_dividend_date = None
        if ex_date_raw:
            from datetime import datetime, timezone

            try:
                if isinstance(ex_date_raw, (int, float)):
                    ex_dividend_date = datetime.fromtimestamp(
                        ex_date_raw, tz=timezone.utc
                    ).strftime("%Y-%m-%d")
                else:
                    ex_dividend_date = str(ex_date_raw)[:10]
            except Exception:
                ex_dividend_date = str(ex_date_raw)[:10]

        return {
            "ticker": ticker,
            "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
            "ex_dividend_date": ex_dividend_date,
        }

    except Exception as e:
        logger.debug("無法取得 %s 股息資訊：%s", ticker, e)
        return {"ticker": ticker, "dividend_yield": None, "ex_dividend_date": None}


def get_dividend_info(ticker: str) -> dict:
    """取得股息資訊。結果快取避免重複呼叫 yfinance。"""
    return _cached_fetch(
        _dividend_cache, ticker, DISK_KEY_DIVIDEND, DISK_DIVIDEND_TTL, _fetch_dividend_from_yf
    )


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
        _rate_limiter.wait()
        session = _get_session()
        ticker_obj = yf.Ticker(yf_ticker, session=session)
        hist = ticker_obj.history(period="5d")

        if hist is not None and not hist.empty:
            rate = float(hist["Close"].dropna().iloc[-1])
            logger.info("匯率 %s → %s = %.4f", holding_cur, display_cur, rate)
            return rate

        # 嘗試反向查詢
        yf_ticker_rev = f"{display_cur}{holding_cur}=X"
        _rate_limiter.wait()
        ticker_obj_rev = yf.Ticker(yf_ticker_rev, session=session)
        hist_rev = ticker_obj_rev.history(period="5d")

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
        t = yf.Ticker(ticker, session=_get_session())
        fd = t.funds_data
        if fd is None:
            return None
        top = fd.top_holdings
        if top is None or top.empty:
            return None

        cols = list(top.columns)
        logger.debug("%s top_holdings columns=%s, index=%s", ticker, cols, top.index.name)

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
        logger.info(
            "%s ETF 成分股取得 %d 筆（前 %d）", ticker, len(result), ETF_TOP_N
        )
        return result if result else None
    except Exception as e:
        logger.debug("%s 非 ETF 或取得成分股失敗：%s", ticker, e)
        return None


_ETF_NOT_FOUND_SENTINEL: list[dict] = []  # 空 list 作為「非 ETF」的快取標記


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
