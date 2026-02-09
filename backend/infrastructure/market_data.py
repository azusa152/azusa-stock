"""
Infrastructure — 市場資料適配器 (yfinance)。
負責外部 API 呼叫、快取管理。
所有呼叫皆以 try/except 包裹，失敗時回傳結構化降級結果。
"""

from typing import Optional

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
from domain.enums import MarketSentiment, MoatStatus
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# TTL 快取：避免每次頁面載入都重複呼叫 yfinance（預設 5 分鐘）
# ---------------------------------------------------------------------------
_signals_cache: TTLCache = TTLCache(maxsize=200, ttl=300)
_moat_cache: TTLCache = TTLCache(maxsize=200, ttl=300)


def _get_session() -> cffi_requests.Session:
    """建立模擬 Chrome 瀏覽器的 Session，以繞過 Yahoo Finance 的 bot 防護。"""
    return cffi_requests.Session(impersonate="chrome")


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
        logger.debug("%s 技術訊號命中快取。", ticker)
        return cached

    try:
        logger.debug("取得 %s 技術訊號（快取未命中）...", ticker)
        stock = yf.Ticker(ticker, session=_get_session())
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 60:
            logger.warning("%s 歷史資料不足（%d 筆），無法計算技術指標。", ticker, len(hist))
            return {"error": f"⚠️ {ticker} 歷史資料不足，無法計算技術指標。"}

        closes = hist["Close"].tolist()
        volumes = hist["Volume"].tolist() if "Volume" in hist.columns else []
        current_price = round(closes[-1], 2)

        # 使用 domain 層的純計算函式
        rsi = compute_rsi(closes)
        ma200 = compute_moving_average(closes, 200)
        ma60 = compute_moving_average(closes, 60)
        bias = compute_bias(current_price, ma60) if ma60 else None
        volume_ratio = compute_volume_ratio(volumes)

        # 狀態判斷（表示層邏輯，保留在此處）
        status_parts: list[str] = []

        if rsi is not None:
            if rsi < 30:
                status_parts.append(f"🟢 RSI={rsi} 超賣區間（可能是機會）")
            elif rsi > 70:
                status_parts.append(f"🔴 RSI={rsi} 超買區間（留意回檔）")
            else:
                status_parts.append(f"⚪ RSI={rsi} 中性")

        if ma200 is not None:
            if current_price < ma200:
                status_parts.append(f"🔴 股價 {current_price} 跌破 200MA ({ma200})")
            else:
                status_parts.append(f"🟢 股價 {current_price} 站穩 200MA ({ma200})")
        else:
            status_parts.append("⚠️ 資料不足 200 天，無法計算 200MA")

        if ma60 is not None:
            if current_price < ma60:
                status_parts.append(f"🔴 股價 {current_price} 跌破 60MA ({ma60})")
            else:
                status_parts.append(f"🟢 股價 {current_price} 站穩 60MA ({ma60})")

        if bias is not None:
            if bias > 20:
                status_parts.append(f"🔴 乖離率 {bias}% 過熱")
            elif bias < -20:
                status_parts.append(f"🟢 乖離率 {bias}% 超跌")

        logger.info(
            "%s 技術訊號：price=%.2f, RSI=%s, 200MA=%s, 60MA=%s, Bias=%s%%, VolRatio=%s",
            ticker, current_price, rsi, ma200, ma60, bias, volume_ratio,
        )

        # 機構持倉 (best-effort，失敗不影響整體回傳)
        institutional_holders = None
        try:
            holders_df = stock.institutional_holders
            if holders_df is not None and not holders_df.empty:
                top5 = holders_df.head(5)
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
        return result

    except Exception as e:
        logger.error("無法取得 %s 技術訊號：%s", ticker, e, exc_info=True)
        return {"error": f"⚠️ 無法取得 {ticker} 技術訊號：{e}"}


# ===========================================================================
# 護城河趨勢（毛利率 YoY）
# ===========================================================================


def analyze_moat_trend(ticker: str) -> dict:
    """
    比較最近一季 vs 去年同期的毛利率 (YoY)。
    回傳結構化結果，含 moat 狀態欄位。結果快取 5 分鐘。
    """
    cached = _moat_cache.get(ticker)
    if cached is not None:
        logger.debug("%s 護城河分析命中快取。", ticker)
        return cached

    try:
        logger.debug("分析 %s 護城河（毛利率 YoY，快取未命中）...", ticker)
        stock = yf.Ticker(ticker, session=_get_session())
        financials = stock.quarterly_financials

        if financials is None or financials.empty:
            logger.warning("%s 無法取得季報資料。", ticker)
            result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
            _moat_cache[ticker] = result
            return result

        columns = financials.columns.tolist()

        if len(columns) < 5:
            logger.warning("%s 季報資料不足（%d 季），需至少 5 季。", ticker, len(columns))
            result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
            _moat_cache[ticker] = result
            return result

        latest_col = columns[0]
        yoy_col = columns[4]

        def _get_gross_margin(col) -> Optional[float]:
            try:
                gross_profit = financials.loc["Gross Profit", col]
                revenue = financials.loc["Total Revenue", col]
                if revenue and revenue != 0:
                    return round(float(gross_profit) / float(revenue) * 100, 2)
            except KeyError:
                pass
            return None

        current_margin = _get_gross_margin(latest_col)
        previous_margin = _get_gross_margin(yoy_col)

        # 使用 domain 層的純判定函式
        moat_status, change = determine_moat_status(current_margin, previous_margin)

        if moat_status == MoatStatus.NOT_AVAILABLE:
            result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
            _moat_cache[ticker] = result
            return result

        result: dict = {
            "ticker": ticker,
            "current_quarter": str(latest_col.date()) if hasattr(latest_col, "date") else str(latest_col),
            "yoy_quarter": str(yoy_col.date()) if hasattr(yoy_col, "date") else str(yoy_col),
            "current_margin": current_margin,
            "previous_margin": previous_margin,
            "change": change,
            "moat": moat_status.value,
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
        return result

    except Exception as e:
        logger.error("無法分析 %s 護城河：%s", ticker, e, exc_info=True)
        result = {"ticker": ticker, "moat": MoatStatus.NOT_AVAILABLE.value, "details": "N/A failed to get new data"}
        _moat_cache[ticker] = result
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
