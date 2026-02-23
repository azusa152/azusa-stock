"""
Domain — 純粹的分析計算函式。
不依賴任何外部服務、資料庫或框架，僅接收資料並回傳結果。
可獨立測試。
"""

import bisect
from typing import Optional

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    BIAS_OVERSOLD_THRESHOLD,
    BIAS_WEAKENING_THRESHOLD,
    CATEGORY_RSI_OFFSET,
    CNN_FG_EXTREME_FEAR,
    CNN_FG_FEAR,
    CNN_FG_GREED,
    CNN_FG_NEUTRAL_HIGH,
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


def compute_rsi(closes: list[float], period: int = RSI_PERIOD) -> Optional[float]:
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


def compute_bias(price: float, ma: float) -> Optional[float]:
    """計算乖離率 (%)：(現價 - MA) / MA * 100。可用於任意移動平均線（MA60、MA200 等）。"""
    if ma and ma != 0:
        return round((price - ma) / ma * 100, 2)
    return None


def compute_daily_change_pct(current: float, previous: float) -> Optional[float]:
    """計算日漲跌百分比。previous 為 0 時回傳 None。"""
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 2)


def compute_volume_ratio(volumes: list[float]) -> Optional[float]:
    """計算量比：近 5 日均量 / 近 20 日均量。需至少 20 筆資料。"""
    if len(volumes) < VOLUME_RATIO_LONG_DAYS:
        return None
    avg_vol_5 = sum(volumes[-VOLUME_RATIO_SHORT_DAYS:]) / VOLUME_RATIO_SHORT_DAYS
    avg_vol_20 = sum(volumes[-VOLUME_RATIO_LONG_DAYS:]) / VOLUME_RATIO_LONG_DAYS
    if avg_vol_20 > 0:
        return round(avg_vol_5 / avg_vol_20, 2)
    return None


def compute_moving_average(values: list[float], window: int) -> Optional[float]:
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
) -> Optional[float]:
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
    bias_percentile: Optional[float],
    volume_ratio: Optional[float],
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
    current_margin: Optional[float],
    previous_margin: Optional[float],
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
    rsi: Optional[float],
    bias: Optional[float],
    bias_200: Optional[float] = None,
    category: Optional[str] = None,
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
        elif bias_200 > MA200_HIGH_DEVIATION_THRESHOLD:
            if signal == ScanSignal.CAUTION_HIGH:
                signal = ScanSignal.OVERHEATED

    return signal


# ---------------------------------------------------------------------------
# 恐懼與貪婪指數分析
# ---------------------------------------------------------------------------


def classify_vix(vix_value: Optional[float]) -> FearGreedLevel:
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


def classify_cnn_fear_greed(score: Optional[int]) -> FearGreedLevel:
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


def _vix_to_score(vix_value: Optional[float]) -> int:
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

    return 50  # fallback（理論上不會執行到此）


def compute_composite_fear_greed(
    vix_value: Optional[float],
    cnn_score: Optional[int],
) -> tuple[FearGreedLevel, int]:
    """
    恐懼與貪婪指數：CNN 優先，VIX 備援。

    CNN Fear & Greed Index 本身已是 7 項指標（含 VIX）的綜合分數，
    直接採用可避免 VIX 被重複加權。VIX 僅在 CNN 不可用時作為備援。

    回傳 (等級, 0–100 分數)。
    純函式，無副作用。
    """
    if cnn_score is not None:
        composite = cnn_score
    elif vix_value is not None:
        composite = _vix_to_score(vix_value)
    else:
        return FearGreedLevel.NOT_AVAILABLE, 50

    composite = max(0, min(100, composite))
    level = classify_cnn_fear_greed(composite)
    return level, composite


# ---------------------------------------------------------------------------
# 投資組合績效
# ---------------------------------------------------------------------------


def compute_twr(snapshots: list[dict]) -> Optional[float]:
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
