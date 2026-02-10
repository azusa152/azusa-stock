"""
Infrastructure — 市場資料適配器 (yfinance)。
負責外部 API 呼叫、快取管理、速率限制。
所有呼叫皆以 try/except 包裹，失敗時回傳結構化降級結果。
"""

import threading
import time
from typing import Optional

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
from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    BIAS_OVERSOLD_THRESHOLD,
    CURL_CFFI_IMPERSONATE,
    DISK_CACHE_DIR,
    DISK_CACHE_SIZE_LIMIT,
    DISK_DIVIDEND_TTL,
    DISK_EARNINGS_TTL,
    DISK_MOAT_TTL,
    DISK_SIGNALS_TTL,
    DIVIDEND_CACHE_MAXSIZE,
    DIVIDEND_CACHE_TTL,
    EARNINGS_CACHE_MAXSIZE,
    EARNINGS_CACHE_TTL,
    INSTITUTIONAL_HOLDERS_TOP_N,
    MA200_WINDOW,
    MA60_WINDOW,
    MARGIN_TREND_QUARTERS,
    MIN_HISTORY_DAYS_FOR_SIGNALS,
    MOAT_CACHE_MAXSIZE,
    MOAT_CACHE_TTL,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
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


def _get_session() -> cffi_requests.Session:
    """建立模擬 Chrome 瀏覽器的 Session，以繞過 Yahoo Finance 的 bot 防護。"""
    return cffi_requests.Session(impersonate=CURL_CFFI_IMPERSONATE)


# ===========================================================================
# 技術面訊號
# ===========================================================================


def get_technical_signals(ticker: str) -> Optional[dict]:
    """
    取得技術面訊號：RSI(14)、現價、200MA、60MA、Bias(%)、Volume Ratio。
    回傳 dict 包含數值與狀態描述。結果快取 5 分鐘。
    """
    cached = _signals_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 技術訊號命中 L1 快取。", ticker)
        return cached

    # L2: 磁碟快取
    disk_key = f"signals:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("%s 技術訊號命中 L2 磁碟快取。", ticker)
        _signals_cache[ticker] = disk_cached
        return disk_cached

    try:
        logger.debug("取得 %s 技術訊號（L1+L2 皆未命中）...", ticker)
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        hist = stock.history(period=YFINANCE_HISTORY_PERIOD)

        if hist.empty or len(hist) < MIN_HISTORY_DAYS_FOR_SIGNALS:
            logger.warning("%s 歷史資料不足（%d 筆），無法計算技術指標。", ticker, len(hist))
            return {"error": f"⚠️ {ticker} 歷史資料不足，無法計算技術指標。"}

        closes = hist["Close"].tolist()
        volumes = hist["Volume"].tolist() if "Volume" in hist.columns else []
        current_price = round(closes[-1], 2)

        # 使用 domain 層的純計算函式
        rsi = compute_rsi(closes)
        ma200 = compute_moving_average(closes, MA200_WINDOW)
        ma60 = compute_moving_average(closes, MA60_WINDOW)
        bias = compute_bias(current_price, ma60) if ma60 else None
        volume_ratio = compute_volume_ratio(volumes)

        # 狀態判斷（表示層邏輯，保留在此處）
        status_parts: list[str] = []

        if rsi is not None:
            if rsi < RSI_OVERSOLD:
                status_parts.append(f"🟢 RSI={rsi} 超賣區間（可能是機會）")
            elif rsi > RSI_OVERBOUGHT:
                status_parts.append(f"🔴 RSI={rsi} 超買區間（留意回檔）")
            else:
                status_parts.append(f"⚪ RSI={rsi} 中性")

        if ma200 is not None:
            if current_price < ma200:
                status_parts.append(f"🔴 股價 {current_price} 跌破 200MA ({ma200})")
            else:
                status_parts.append(f"🟢 股價 {current_price} 站穩 200MA ({ma200})")
            else:
                status_parts.append(f"⚠️ 資料不足 {MA200_WINDOW} 天，無法計算 200MA")

        if ma60 is not None:
            if current_price < ma60:
                status_parts.append(f"🔴 股價 {current_price} 跌破 60MA ({ma60})")
            else:
                status_parts.append(f"🟢 股價 {current_price} 站穩 60MA ({ma60})")

        if bias is not None:
            if bias > BIAS_OVERHEATED_THRESHOLD:
                status_parts.append(f"🔴 乖離率 {bias}% 過熱")
            elif bias < BIAS_OVERSOLD_THRESHOLD:
                status_parts.append(f"🟢 乖離率 {bias}% 超跌")

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

        result = {
            "ticker": ticker,
            "price": current_price,
            "rsi": rsi,
            "ma200": ma200,
            "ma60": ma60,
            "bias": bias,
            "volume_ratio": volume_ratio,
            "status": status_parts,
            "institutional_holders": institutional_holders,
        }
        _signals_cache[ticker] = result
        _disk_set(disk_key, result, DISK_SIGNALS_TTL)
        return result

    except Exception as e:
        logger.error("無法取得 %s 技術訊號：%s", ticker, e, exc_info=True)
        return {"error": f"⚠️ 無法取得 {ticker} 技術訊號：{e}"}


# ===========================================================================
# 護城河趨勢（毛利率 YoY）
# ===========================================================================


def analyze_moat_trend(ticker: str) -> dict:
    """
    分析護城河趨勢：回傳最近 5 季毛利率走勢、YoY 變化與 moat 狀態。
    結果快取 1 小時（季報不會頻繁變動）。
    """
    cached = _moat_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 護城河分析命中 L1 快取。", ticker)
        return cached

    # L2: 磁碟快取
    disk_key = f"moat:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("%s 護城河分析命中 L2 磁碟快取。", ticker)
        _moat_cache[ticker] = disk_cached
        return disk_cached

    try:
        logger.debug("分析 %s 護城河（L1+L2 皆未命中）...", ticker)
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        financials = stock.quarterly_financials

        if financials is None or financials.empty:
            logger.warning("%s 無法取得季報資料。", ticker)
            result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
            _moat_cache[ticker] = result
            _disk_set(disk_key, result, DISK_MOAT_TTL)
            return result

        columns = financials.columns.tolist()

        if len(columns) < 2:
            logger.warning("%s 季報資料不足（%d 季），無法分析。", ticker, len(columns))
            result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
            _moat_cache[ticker] = result
            _disk_set(disk_key, result, DISK_MOAT_TTL)
            return result

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
            result = {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
                "margin_trend": margin_trend,
            }
            _moat_cache[ticker] = result
            _disk_set(disk_key, result, DISK_MOAT_TTL)
            return result

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

        if moat_status == MoatStatus.DETERIORATING:
            logger.warning(
                "%s 護城河惡化：毛利率 %.2f%% → 去年同期 %.2f%%（下降 %.2f pp）",
                ticker, current_margin, previous_margin, abs(change),
            )
            result["details"] = (
                f"毛利率衰退！{current_margin}% → 去年同期 {previous_margin}%"
                f"（下降 {abs(change)} 個百分點）— 護城河鬆動！"
            )
        else:
            logger.info(
                "%s 護城河穩健：毛利率 %.2f%% vs 去年同期 %.2f%%（%+.2f pp）",
                ticker, current_margin, previous_margin, change,
            )
            result["details"] = (
                f"毛利率穩健：{current_margin}% vs 去年同期 {previous_margin}%"
                f"（{'+' if change >= 0 else ''}{change} 個百分點）"
            )

        _moat_cache[ticker] = result
        _disk_set(disk_key, result, DISK_MOAT_TTL)
        return result

    except Exception as e:
        logger.error("無法分析 %s 護城河：%s", ticker, e, exc_info=True)
        result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
        _moat_cache[ticker] = result
        _disk_set(disk_key, result, DISK_MOAT_TTL)
        return result


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


def get_earnings_date(ticker: str) -> dict:
    """
    取得下次財報日期。結果快取 24 小時。
    """
    cached = _earnings_cache.get(ticker)
    if cached is not None:
        return cached

    # L2: 磁碟快取
    disk_key = f"earnings:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("%s 財報日期命中 L2 磁碟快取。", ticker)
        _earnings_cache[ticker] = disk_cached
        return disk_cached

    try:
        logger.debug("取得 %s 財報日期（L1+L2 皆未命中）...", ticker)
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        cal = stock.calendar

        result: dict = {"ticker": ticker}

        if cal is not None:
            # yfinance calendar 可能回傳 dict 或 DataFrame
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
                # DataFrame 格式
                if "Earnings Date" in cal.index:
                    val = cal.loc["Earnings Date"].iloc[0]
                    result["earnings_date"] = (
                        val.isoformat()[:10]
                        if hasattr(val, "isoformat")
                        else str(val)[:10]
                    )

        if "earnings_date" not in result:
            result["earnings_date"] = None

        _earnings_cache[ticker] = result
        _disk_set(disk_key, result, DISK_EARNINGS_TTL)
        return result

    except Exception as e:
        logger.debug("無法取得 %s 財報日期：%s", ticker, e)
        result = {"ticker": ticker, "earnings_date": None}
        _earnings_cache[ticker] = result
        _disk_set(disk_key, result, DISK_EARNINGS_TTL)
        return result


# ===========================================================================
# 股息資訊 (Dividend Info)
# ===========================================================================


def get_dividend_info(ticker: str) -> dict:
    """
    取得股息資訊。結果快取避免重複呼叫 yfinance。
    """
    cached = _dividend_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 股息資訊命中 L1 快取。", ticker)
        return cached

    # L2: 磁碟快取
    disk_key = f"dividend:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        logger.debug("%s 股息資訊命中 L2 磁碟快取。", ticker)
        _dividend_cache[ticker] = disk_cached
        return disk_cached

    try:
        _rate_limiter.wait()
        stock = yf.Ticker(ticker, session=_get_session())
        _rate_limiter.wait()
        info = stock.info or {}

        dividend_yield = info.get("dividendYield")
        ex_date_raw = info.get("exDividendDate")

        # exDividendDate 通常是 Unix timestamp
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

        result = {
            "ticker": ticker,
            "dividend_yield": round(dividend_yield * 100, 2) if dividend_yield else None,
            "ex_dividend_date": ex_dividend_date,
        }
        _dividend_cache[ticker] = result
        _disk_set(disk_key, result, DISK_DIVIDEND_TTL)
        return result

    except Exception as e:
        logger.debug("無法取得 %s 股息資訊：%s", ticker, e)
        result = {"ticker": ticker, "dividend_yield": None, "ex_dividend_date": None}
        _dividend_cache[ticker] = result
        _disk_set(disk_key, result, DISK_DIVIDEND_TTL)
        return result
