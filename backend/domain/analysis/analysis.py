"""
Domain — 純粹的分析計算函式。
不依賴任何外部服務、資料庫或框架，僅接收資料並回傳結果。
可獨立測試。
"""

import bisect
import math
from datetime import UTC, datetime

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    BIAS_OVERSOLD_THRESHOLD,
    BIAS_WEAKENING_THRESHOLD,
    CATEGORY_RSI_OFFSET,
    CNN_FG_EXTREME_FEAR,
    CNN_FG_FEAR,
    CNN_FG_GREED,
    CNN_FG_NEUTRAL_HIGH,
    FG_BREADTH_MULT,
    FG_COMPONENT_WEIGHTS,
    FG_JUNK_BOND_MULT,
    FG_LOOKBACK_DAYS,
    FG_MA_WINDOW,
    FG_MOMENTUM_MA_MULT,
    FG_MOMENTUM_RSI_WEIGHT,
    FG_PRICE_STRENGTH_MULT,
    FG_SAFE_HAVEN_MULT,
    FG_SECTOR_ROTATION_MULT,
    FG_VIX_BASE,
    FG_VIX_OFFSET,
    FG_VIX_SLOPE,
    JP_VI_BASE,
    JP_VI_OFFSET,
    JP_VI_SLOPE,
    MA200_DEEP_DEVIATION_THRESHOLD,
    MA200_HIGH_DEVIATION_THRESHOLD,
    MARKET_BEARISH_MAX_PCT,
    MARKET_BULLISH_MAX_PCT,
    MARKET_NEUTRAL_MAX_PCT,
    MARKET_STRONG_BULLISH_MAX_PCT,
    MOAT_MARGIN_DETERIORATION_THRESHOLD,
    ROGUE_WAVE_BIAS_PERCENTILE,
    ROGUE_WAVE_MIN_HISTORY_DAYS,
    ROGUE_WAVE_VOLUME_RATIO_THRESHOLD,
    RSI_APPROACHING_BUY_THRESHOLD,
    RSI_CONTRARIAN_BUY_THRESHOLD,
    RSI_OVERBOUGHT,
    RSI_PERIOD,
    RSI_WEAKENING_THRESHOLD,
    SECONDS_PER_DAY,
    TW_VOL_BASE,
    TW_VOL_OFFSET,
    TW_VOL_SLOPE,
    VIX_EXTREME_FEAR,
    VIX_FEAR,
    VIX_GREED,
    VIX_NEUTRAL_LOW,
    VIX_SCORE_BREAKPOINTS,
    VIX_SCORE_CEILING,
    VIX_SCORE_CEILING_VIX,
    VIX_SCORE_FLOOR,
    VIX_SCORE_FLOOR_VIX,
    VOLUME_RATIO_LONG_DAYS,
    VOLUME_RATIO_SHORT_DAYS,
)
from domain.enums import FearGreedLevel, MarketSentiment, MoatStatus, ScanSignal

# ---------------------------------------------------------------------------
# 技術指標計算
# ---------------------------------------------------------------------------


def compute_rsi(closes: list[float], period: int = RSI_PERIOD) -> float | None:
    """
    以 Wilder's Smoothed Method 計算 RSI。
    需要至少 period+1 筆收盤價。純函式，無副作用。
    """
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for d in deltas[period:]:
        gain = d if d > 0 else 0.0
        loss = -d if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def compute_bias(price: float, ma: float) -> float | None:
    """計算乖離率 (%)：(現價 - MA) / MA * 100。可用於任意移動平均線（MA60、MA200 等）。"""
    if ma and ma != 0:
        return round((price - ma) / ma * 100, 2)
    return None


def compute_daily_change_pct(current: float, previous: float) -> float | None:
    """計算日漲跌百分比。previous 為 0 時回傳 None。"""
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 2)


def compute_volume_ratio(volumes: list[float]) -> float | None:
    """計算量比：近 5 日均量 / 近 20 日均量。需至少 20 筆資料。"""
    if len(volumes) < VOLUME_RATIO_LONG_DAYS:
        return None
    avg_vol_5 = sum(volumes[-VOLUME_RATIO_SHORT_DAYS:]) / VOLUME_RATIO_SHORT_DAYS
    avg_vol_20 = sum(volumes[-VOLUME_RATIO_LONG_DAYS:]) / VOLUME_RATIO_LONG_DAYS
    if avg_vol_20 > 0:
        return round(avg_vol_5 / avg_vol_20, 2)
    return None


def compute_moving_average(values: list[float], window: int) -> float | None:
    """計算簡單移動平均線。需至少 window 筆資料。"""
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 2)


# ---------------------------------------------------------------------------
# Rogue Wave (瘋狗浪) — 歷史乖離率百分位 + 極端情緒偵測
# ---------------------------------------------------------------------------


def compute_bias_percentile(
    current_bias: float,
    historical_biases: list[float],
) -> float | None:
    """
    計算當前乖離率在歷史分佈中的百分位數（0.0–100.0）。

    Input:
        current_bias       — 當前乖離率
        historical_biases  — 已排序的歷史乖離率列表（升序）

    若歷史資料不足 ROGUE_WAVE_MIN_HISTORY_DAYS 筆，回傳 None。
    使用 bisect_left 達到 O(log n) 搜尋效率。
    純函式，無副作用。
    """
    if len(historical_biases) < ROGUE_WAVE_MIN_HISTORY_DAYS:
        return None
    rank = bisect.bisect_left(historical_biases, current_bias)
    return round(rank / len(historical_biases) * 100, 2)


def detect_rogue_wave(
    bias_percentile: float | None,
    volume_ratio: float | None,
) -> bool:
    """
    偵測瘋狗浪訊號：乖離率達歷史極端高位 AND 成交量明顯放大。

    條件：
        bias_percentile >= ROGUE_WAVE_BIAS_PERCENTILE (95)
        volume_ratio    >= ROGUE_WAVE_VOLUME_RATIO_THRESHOLD (1.5)

    任一輸入為 None 時回傳 False。
    純函式，無副作用。
    """
    if bias_percentile is None or volume_ratio is None:
        return False
    return (
        bias_percentile >= ROGUE_WAVE_BIAS_PERCENTILE
        and volume_ratio >= ROGUE_WAVE_VOLUME_RATIO_THRESHOLD
    )


# ---------------------------------------------------------------------------
# 護城河判定
# ---------------------------------------------------------------------------


def determine_moat_status(
    current_margin: float | None,
    previous_margin: float | None,
) -> tuple[MoatStatus, float]:
    """
    根據毛利率變化判定護城河狀態。
    回傳 (狀態, 變化百分點)。
    """
    if current_margin is None or previous_margin is None:
        return MoatStatus.NOT_AVAILABLE, 0.0

    change = round(current_margin - previous_margin, 2)

    if change < MOAT_MARGIN_DETERIORATION_THRESHOLD:
        return MoatStatus.DETERIORATING, change

    return MoatStatus.STABLE, change


# ---------------------------------------------------------------------------
# 市場情緒判定
# ---------------------------------------------------------------------------


def determine_market_sentiment(
    below_count: int,
    valid_count: int,
) -> tuple[MarketSentiment, float]:
    """
    根據跌破 60MA 的風向球比例判定市場情緒（5 階段）。
    回傳 (情緒, 跌破百分比)。

    | 階段            | 跌破 60MA %       | 天氣   |
    |-----------------|-------------------|--------|
    | STRONG_BULLISH  | 0–10%             | ☀️ 晴  |
    | BULLISH         | 10–30%            | 🌤️ 晴時多雲 |
    | NEUTRAL         | 30–50%            | ⛅ 多雲 |
    | BEARISH         | 50–70%            | 🌧️ 雨  |
    | STRONG_BEARISH  | >70%              | ⛈️ 暴風雨 |

    valid_count == 0 → BULLISH（無資料時預設樂觀，避免空持倉時觸發警報）。
    """
    if valid_count == 0:
        return MarketSentiment.BULLISH, 0.0

    pct = round(below_count / valid_count * 100, 1)

    if pct <= MARKET_STRONG_BULLISH_MAX_PCT:
        return MarketSentiment.STRONG_BULLISH, pct
    if pct <= MARKET_BULLISH_MAX_PCT:
        return MarketSentiment.BULLISH, pct
    if pct <= MARKET_NEUTRAL_MAX_PCT:
        return MarketSentiment.NEUTRAL, pct
    if pct <= MARKET_BEARISH_MAX_PCT:
        return MarketSentiment.BEARISH, pct
    return MarketSentiment.STRONG_BEARISH, pct


# ---------------------------------------------------------------------------
# 三層漏斗決策引擎
# ---------------------------------------------------------------------------


def determine_scan_signal(
    moat: str,
    rsi: float | None,
    bias: float | None,
    bias_200: float | None = None,
    category: str | None = None,
) -> ScanSignal:
    """
    9 優先級掃描訊號決策引擎（兩階段架構）。
    純函式，不依賴外部狀態。None 值視為「條件不成立」，安全落穿至 NORMAL。

    ── Phase 1：分類感知優先漏斗 ──────────────────────────────────────────────
    依 CATEGORY_RSI_OFFSET 計算 RSI 偏移，對買賣雙側對稱套用（高 beta 擴大區間）。

    | 優先  | 條件                                        | 訊號             |
    |-------|---------------------------------------------|------------------|
    | P1    | moat == DETERIORATING                       | THESIS_BROKEN    |
    | P2    | bias < -20 AND rsi < (35+offset)            | DEEP_VALUE       |
    | P3    | bias < -20                                  | OVERSOLD         |
    | P4    | rsi < (35+offset) AND bias < 20             | CONTRARIAN_BUY   |
    | P4.5  | rsi < (37+offset) AND bias < -15            | APPROACHING_BUY  |
    | P5    | bias > 20 AND rsi > (70+offset)             | OVERHEATED       |
    | P6    | bias > 20 OR rsi > (70+offset)              | CAUTION_HIGH     |
    | P7    | bias < -15 AND rsi < (38+offset)            | WEAKENING        |
    | P8    | 其他                                         | NORMAL           |

    ── Phase 2：對稱 MA200 放大器 ──────────────────────────────────────────────
    - 買側（bias_200 < -15%）：WEAKENING → APPROACHING_BUY → CONTRARIAN_BUY
    - 賣側（bias_200 > +20%，非對稱：市場長期向上偏移）：CAUTION_HIGH → OVERHEATED
    - P1-P3 及已確認的 OVERHEATED/NORMAL 不受影響。

    ── category 對應的 RSI 偏移 ────────────────────────────────────────────────
    Trend_Setter: 0, Moat: +1, Growth: +2, Bond: -3, Cash: 0
    公式：round((beta - 1.0) * 4)，來源：CATEGORY_FALLBACK_BETA

    ── None 處理設計決策 ────────────────────────────────────────────────────────
    - rsi=None  → P2, P4, P4.5, P5(RSI), P6(RSI), P7 跳過；P3 在 bias < -20 時仍觸發。
    - bias=None → P2, P3, P4.5, P5(bias), P6(bias), P7 跳過。
    - P4 with bias=None：允許 CONTRARIAN_BUY（RSI < threshold 已足夠，避免新掛牌股票漏報）。
    - bias_200=None → Phase 2 放大器整體跳過。
    - Both None → 僅 P1 (THESIS_BROKEN) 或 P8 (NORMAL) 可觸達。
    """
    # ── Phase 1：分類感知優先漏斗 ────────────────────────────────────────────
    rsi_offset = CATEGORY_RSI_OFFSET.get(category, 0) if category else 0

    rsi_contrarian = RSI_CONTRARIAN_BUY_THRESHOLD + rsi_offset
    rsi_approaching = RSI_APPROACHING_BUY_THRESHOLD + rsi_offset
    rsi_weakening = RSI_WEAKENING_THRESHOLD + rsi_offset
    rsi_overbought = RSI_OVERBOUGHT + rsi_offset

    # P1: 護城河惡化 — 論文破裂，優先順序最高
    if moat == MoatStatus.DETERIORATING.value:
        return ScanSignal.THESIS_BROKEN

    # P2: 雙重確認深度價值（最高確信度買入訊號）
    if (
        bias is not None
        and bias < BIAS_OVERSOLD_THRESHOLD
        and rsi is not None
        and rsi < rsi_contrarian
    ):
        signal = ScanSignal.DEEP_VALUE

    # P3: 乖離率極端（e.g. bias=-31%, RSI未確認）
    elif bias is not None and bias < BIAS_OVERSOLD_THRESHOLD:
        signal = ScanSignal.OVERSOLD

    # P4: RSI 超賣 + 乖離率未過熱（防止矛盾訊號）
    elif (
        rsi is not None
        and rsi < rsi_contrarian
        and (bias is None or bias < BIAS_OVERHEATED_THRESHOLD)
    ):
        signal = ScanSignal.CONTRARIAN_BUY

    # P4.5: 接近買入區（RSI 進入累積區，bias 偏弱但未達極端）
    elif (
        rsi is not None
        and rsi < rsi_approaching
        and bias is not None
        and bias < BIAS_WEAKENING_THRESHOLD
    ):
        signal = ScanSignal.APPROACHING_BUY

    # P5: 雙重確認過熱（最高確信度賣出警示）
    elif (
        bias is not None
        and bias > BIAS_OVERHEATED_THRESHOLD
        and rsi is not None
        and rsi > rsi_overbought
    ):
        signal = ScanSignal.OVERHEATED

    # P6: 單一指標過熱警示
    elif (bias is not None and bias > BIAS_OVERHEATED_THRESHOLD) or (
        rsi is not None and rsi > rsi_overbought
    ):
        signal = ScanSignal.CAUTION_HIGH

    # P7: 早期轉弱（收緊閾值以減少警報疲勞）
    elif (
        bias is not None
        and bias < BIAS_WEAKENING_THRESHOLD
        and rsi is not None
        and rsi < rsi_weakening
    ):
        signal = ScanSignal.WEAKENING

    # P8: 真正中性
    else:
        signal = ScanSignal.NORMAL

    # ── Phase 2：對稱 MA200 放大器 ──────────────────────────────────────────
    if bias_200 is not None:
        # 買側：深度偏離 MA200 → 升級信號（均值回歸確認）
        if bias_200 < MA200_DEEP_DEVIATION_THRESHOLD:
            if signal == ScanSignal.WEAKENING:
                signal = ScanSignal.APPROACHING_BUY
            elif signal == ScanSignal.APPROACHING_BUY:
                signal = ScanSignal.CONTRARIAN_BUY

        # 賣側：顯著高於 MA200 → 升級至過熱（+20% 非對稱：市場長期向上偏移）
        elif (
            bias_200 > MA200_HIGH_DEVIATION_THRESHOLD
            and signal == ScanSignal.CAUTION_HIGH
        ):
            signal = ScanSignal.OVERHEATED

    return signal


# ---------------------------------------------------------------------------
# 恐懼與貪婪指數分析
# ---------------------------------------------------------------------------


def classify_vix(vix_value: float | None) -> FearGreedLevel:
    """
    根據 VIX 值判定恐懼與貪婪等級。
    VIX > 30 極度恐懼, 20–30 恐懼, 15–20 中性, 10–15 貪婪, < 10 極度貪婪。
    純函式，無副作用。
    """
    if vix_value is None:
        return FearGreedLevel.NOT_AVAILABLE
    if vix_value > VIX_EXTREME_FEAR:  # > 30
        return FearGreedLevel.EXTREME_FEAR
    if vix_value > VIX_FEAR:  # > 20
        return FearGreedLevel.FEAR
    if vix_value > VIX_NEUTRAL_LOW:  # > 15
        return FearGreedLevel.NEUTRAL
    if vix_value > VIX_GREED:  # > 10
        return FearGreedLevel.GREED
    return FearGreedLevel.EXTREME_GREED


def classify_cnn_fear_greed(score: int | None) -> FearGreedLevel:
    """
    根據 CNN Fear & Greed Index（0–100）判定等級。
    0–25 極度恐懼, 25–45 恐懼, 45–55 中性, 55–75 貪婪, 75–100 極度貪婪。
    純函式，無副作用。
    """
    if score is None:
        return FearGreedLevel.NOT_AVAILABLE
    if score <= CNN_FG_EXTREME_FEAR:
        return FearGreedLevel.EXTREME_FEAR
    if score <= CNN_FG_FEAR:
        return FearGreedLevel.FEAR
    if score <= CNN_FG_NEUTRAL_HIGH:
        return FearGreedLevel.NEUTRAL
    if score <= CNN_FG_GREED:
        return FearGreedLevel.GREED
    return FearGreedLevel.EXTREME_GREED


def _vix_to_score(vix_value: float | None) -> int:
    """
    將 VIX 值以分段線性映射至 0–100 恐懼貪婪分數。
    對齊 VIX 區間與 CNN 分數分級閾值，確保 VIX 分類與分數區間一致。
    VIX ≥ 40 → 0, VIX ≤ 8 → 100。
    """
    if vix_value is None:
        return 50

    # 完整分段映射：(VIX 值, 對應分數)，VIX 遞減排列
    points = [
        (VIX_SCORE_FLOOR_VIX, VIX_SCORE_FLOOR),
        *VIX_SCORE_BREAKPOINTS,
        (VIX_SCORE_CEILING_VIX, VIX_SCORE_CEILING),
    ]

    # 超出邊界則鉗制
    if vix_value >= points[0][0]:
        return points[0][1]
    if vix_value <= points[-1][0]:
        return points[-1][1]

    # 找到所在區間並線性內插
    for i in range(len(points) - 1):
        vix_high, score_at_high = points[i]
        vix_low, score_at_low = points[i + 1]
        if vix_value >= vix_low:
            ratio = (vix_high - vix_value) / (vix_high - vix_low)
            return round(score_at_high + ratio * (score_at_low - score_at_high))

    return 50  # fallback（理論上不會執行到此）  # pragma: no cover


def compute_composite_fear_greed(
    vix_value: float | None,
    cnn_score: int | None,
    self_calculated_score: int | None = None,
) -> tuple[FearGreedLevel, int]:
    """
    恐懼與貪婪指數：CNN 優先 → 自計算備援 → VIX 單一備援。

    CNN Fear & Greed Index 本身已是 7 項指標（含 VIX）的綜合分數，
    直接採用可避免 VIX 被重複加權。

    回傳 (等級, 0–100 分數)。
    純函式，無副作用。
    """
    if cnn_score is not None:
        composite = cnn_score
    elif self_calculated_score is not None:
        composite = self_calculated_score
    elif vix_value is not None:
        composite = _vix_to_score(vix_value)
    else:
        return FearGreedLevel.NOT_AVAILABLE, 50

    composite = max(0, min(100, composite))
    level = classify_cnn_fear_greed(composite)
    return level, composite


# ---------------------------------------------------------------------------
# Self-Calculated Fear & Greed — 7 Component Scoring Functions
# Modeled after OnOff.Markets' methodology. Each returns 0–100 (clamped).
# Pure functions, no side effects.
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> int:
    """Clamp a float to [lo, hi] and return as int."""
    return round(max(lo, min(hi, value)))


def _period_return(prices: list[float], lookback: int) -> float | None:
    """
    Compute simple return over the last `lookback` days from a price series.
    Returns None if insufficient data. Result is a percentage (e.g. 3.5 for +3.5%).
    """
    if len(prices) < lookback + 1:
        return None
    start = prices[-(lookback + 1)]
    end = prices[-1]
    if start == 0:
        return None
    return (end / start - 1) * 100


def score_vix_linear(vix_value: float) -> int:
    """
    Continuous linear VIX → 0–100 fear/greed score (no piecewise cliffs).
    Formula: score = FG_VIX_BASE - (vix - FG_VIX_OFFSET) * FG_VIX_SLOPE
    VIX 10 → 90, VIX 20 → 58, VIX 30 → 26, VIX 38+ → 0.
    """
    raw = FG_VIX_BASE - (vix_value - FG_VIX_OFFSET) * FG_VIX_SLOPE
    return _clamp(raw)


def score_price_strength(
    prices: list[float], lookback: int = FG_LOOKBACK_DAYS
) -> int | None:
    """
    SPY 14-day return → 0–100. Formula: 50 + return_pct * FG_PRICE_STRENGTH_MULT.
    Saturates at ±6.25% (score 0 or 100). Returns None if insufficient data.
    """
    ret = _period_return(prices, lookback)
    if ret is None:
        return None
    return _clamp(50.0 + ret * FG_PRICE_STRENGTH_MULT)


def score_momentum_composite(
    prices: list[float],
    rsi_period: int = RSI_PERIOD,
    ma_window: int = FG_MA_WINDOW,
) -> int | None:
    """
    70% RSI(14) + 30% price-vs-MA50 position → 0–100.
    Leverages existing compute_rsi(). Returns None if insufficient data.
    """
    if len(prices) < max(rsi_period + 1, ma_window):
        return None

    rsi = compute_rsi(prices, rsi_period)
    if rsi is None or not math.isfinite(rsi):
        return None  # pragma: no cover

    ma50 = sum(prices[-ma_window:]) / ma_window
    if ma50 == 0 or not math.isfinite(ma50):
        return None  # pragma: no cover
    deviation_pct = (prices[-1] / ma50 - 1) * 100
    if not math.isfinite(deviation_pct):
        return None  # pragma: no cover
    ma_score = _clamp(50.0 + deviation_pct * FG_MOMENTUM_MA_MULT)

    composite = FG_MOMENTUM_RSI_WEIGHT * rsi + (1 - FG_MOMENTUM_RSI_WEIGHT) * ma_score
    return _clamp(composite)


def score_breadth(
    rsp_prices: list[float],
    spy_prices: list[float],
    lookback: int = FG_LOOKBACK_DAYS,
) -> int | None:
    """
    RSP vs SPY 14-day divergence → 0–100.
    Formula: 50 + (rsp_ret - spy_ret) * FG_BREADTH_MULT.
    Saturates at ±2.78% divergence. Returns None if insufficient data.
    """
    rsp_ret = _period_return(rsp_prices, lookback)
    spy_ret = _period_return(spy_prices, lookback)
    if rsp_ret is None or spy_ret is None:
        return None
    return _clamp(50.0 + (rsp_ret - spy_ret) * FG_BREADTH_MULT)


def score_junk_bond_demand(
    hyg_prices: list[float],
    tlt_prices: list[float],
    lookback: int = FG_LOOKBACK_DAYS,
) -> int | None:
    """
    HYG vs TLT 14-day divergence → 0–100.
    Formula: 50 + (hyg_ret - tlt_ret) * FG_JUNK_BOND_MULT.
    HYG outperforming = risk appetite = greed. Returns None if insufficient data.
    """
    hyg_ret = _period_return(hyg_prices, lookback)
    tlt_ret = _period_return(tlt_prices, lookback)
    if hyg_ret is None or tlt_ret is None:
        return None
    return _clamp(50.0 + (hyg_ret - tlt_ret) * FG_JUNK_BOND_MULT)


def score_safe_haven(
    tlt_prices: list[float],
    lookback: int = FG_LOOKBACK_DAYS,
) -> int | None:
    """
    TLT 14-day return (inverted) → 0–100.
    Formula: 50 - tlt_ret * FG_SAFE_HAVEN_MULT.
    Rising TLT = fear for stocks (lower score). Returns None if insufficient data.
    """
    tlt_ret = _period_return(tlt_prices, lookback)
    if tlt_ret is None:
        return None
    return _clamp(50.0 - tlt_ret * FG_SAFE_HAVEN_MULT)


def score_sector_rotation(
    qqq_prices: list[float],
    xlp_prices: list[float],
    lookback: int = FG_LOOKBACK_DAYS,
) -> int | None:
    """
    QQQ vs XLP 14-day divergence → 0–100.
    Formula: 50 + (qqq_ret - xlp_ret) * FG_SECTOR_ROTATION_MULT.
    QQQ (tech/growth) outperforming XLP (defensive) = risk-on = greed.
    Returns None if insufficient data.
    """
    qqq_ret = _period_return(qqq_prices, lookback)
    xlp_ret = _period_return(xlp_prices, lookback)
    if qqq_ret is None or xlp_ret is None:
        return None
    return _clamp(50.0 + (qqq_ret - xlp_ret) * FG_SECTOR_ROTATION_MULT)


def compute_weighted_fear_greed(
    components: dict[str, int | None],
    weights: dict[str, float] | None = None,
) -> tuple[FearGreedLevel, int]:
    """
    Weighted average of available component scores → (FearGreedLevel, 0–100).

    Missing (None) components are excluded and the remaining weights are
    re-normalised so the result is always a valid 0–100 score.
    Returns (NOT_AVAILABLE, 50) when no component data is available.
    """
    if weights is None:
        weights = FG_COMPONENT_WEIGHTS

    available = {k: v for k, v in components.items() if v is not None}
    if not available:
        return FearGreedLevel.NOT_AVAILABLE, 50

    total_weight = sum(weights.get(k, 0.0) for k in available)
    if total_weight == 0:
        return FearGreedLevel.NOT_AVAILABLE, 50

    weighted_sum = sum(v * weights.get(k, 0.0) for k, v in available.items())
    composite = round(weighted_sum / total_weight)
    composite = max(0, min(100, composite))
    level = classify_cnn_fear_greed(composite)
    return level, composite


def score_nikkei_vi_linear(nikkei_vi: float) -> int:
    """
    Continuous linear Nikkei VI → 0–100 fear/greed score.
    Formula: score = JP_VI_BASE - (nikkei_vi - JP_VI_OFFSET) * JP_VI_SLOPE
    NKV 12 → ~90, NKV 20 → ~62, NKV 35 → ~10.
    """
    raw = JP_VI_BASE - (nikkei_vi - JP_VI_OFFSET) * JP_VI_SLOPE
    return _clamp(raw)


def score_tw_vol_linear(vol_pct: float) -> int:
    """
    Continuous linear TAIEX realized volatility (%) → 0–100 fear/greed score.
    Formula: score = TW_VOL_BASE - (vol_pct - TW_VOL_OFFSET) * TW_VOL_SLOPE
    vol 8% → ~90, vol 18% → ~55, vol 30% → ~13.
    """
    raw = TW_VOL_BASE - (vol_pct - TW_VOL_OFFSET) * TW_VOL_SLOPE
    return _clamp(raw)


# ---------------------------------------------------------------------------
# 投資組合績效
# ---------------------------------------------------------------------------


def compute_twr(snapshots: list[dict]) -> float | None:
    """
    以連鎖法計算時間加權報酬率（TWR）。

    每日子期間報酬為 V_t / V_{t-1} - 1，再將所有子期間連乘後減一，
    得到整段期間的 TWR（百分比）。

    此實作不考慮期中現金流，適用於每日快照連續完整的情況。
    若快照中有缺漏日（假日、未觸發 cron），仍可正確跨期計算，
    因為連鎖法只要求相鄰快照的比值，與日曆間距無關。

    Args:
        snapshots: 依 snapshot_date 升冪排列的快照字典列表，
                   每筆須含 ``total_value`` 欄位（float）。

    Returns:
        TWR 百分比（例如 12.3 代表 +12.3%），
        或 None（快照不足兩筆、或首筆 total_value 為零）。
    """
    if len(snapshots) < 2:
        return None

    values = [s.get("total_value") for s in snapshots]
    if any(v is None or v == 0 for v in values[:-1]):
        return None

    product = 1.0
    for i in range(1, len(values)):
        product *= values[i] / values[i - 1]  # type: ignore[operator]

    return round((product - 1) * 100, 2)


def compute_signal_duration(
    signal_since: datetime | None,
    now: datetime,
) -> tuple[int | None, bool]:
    """
    計算訊號持續天數，並判斷是否為「新」訊號（< 24 小時）。

    自動處理 naive datetime（補 UTC tzinfo）。
    純函式，無副作用。

    Returns:
        (duration_days, is_new)
        - duration_days: 訊號持續天數，signal_since 為 None 時回傳 None
        - is_new: 訊號持續不足 24 小時時為 True
    """
    if signal_since is None:
        return None, False
    if signal_since.tzinfo is None:
        signal_since = signal_since.replace(tzinfo=UTC)
    delta = now - signal_since
    return delta.days, delta.total_seconds() < SECONDS_PER_DAY
