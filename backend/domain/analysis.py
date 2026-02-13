"""
Domain — 純粹的分析計算函式。
不依賴任何外部服務、資料庫或框架，僅接收資料並回傳結果。
可獨立測試。
"""

from typing import Optional

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    CNN_FG_EXTREME_FEAR,
    CNN_FG_FEAR,
    CNN_FG_GREED,
    CNN_FG_NEUTRAL_HIGH,
    FG_WEIGHT_CNN,
    FG_WEIGHT_VIX,
    MARKET_CAUTION_BELOW_60MA_PCT,
    MOAT_MARGIN_DETERIORATION_THRESHOLD,
    RSI_CONTRARIAN_BUY_THRESHOLD,
    RSI_PERIOD,
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


def compute_bias(price: float, ma60: float) -> Optional[float]:
    """計算乖離率 (%)：(現價 - 60MA) / 60MA * 100。"""
    if ma60 and ma60 != 0:
        return round((price - ma60) / ma60 * 100, 2)
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
    根據跌破 60MA 的風向球比例判定市場情緒。
    回傳 (情緒, 跌破百分比)。
    """
    if valid_count == 0:
        return MarketSentiment.POSITIVE, 0.0

    pct = round(below_count / valid_count * 100, 1)

    if pct > MARKET_CAUTION_BELOW_60MA_PCT:
        return MarketSentiment.CAUTION, pct

    return MarketSentiment.POSITIVE, pct


# ---------------------------------------------------------------------------
# 三層漏斗決策引擎
# ---------------------------------------------------------------------------


def determine_scan_signal(
    moat: str,
    market_status: str,
    rsi: Optional[float],
    bias: Optional[float],
) -> ScanSignal:
    """
    根據護城河、市場情緒、RSI、乖離率判定掃描訊號。
    純函式，不依賴外部狀態。

    | 條件                                               | 訊號             |
    |----------------------------------------------------|------------------|
    | moat == DETERIORATING                              | THESIS_BROKEN    |
    | market == POSITIVE & moat != DETERIORATING & RSI<35| CONTRARIAN_BUY   |
    | bias > 20                                          | OVERHEATED       |
    | 其他                                                | NORMAL           |
    """
    if moat == MoatStatus.DETERIORATING.value:
        return ScanSignal.THESIS_BROKEN

    if (
        market_status == MarketSentiment.POSITIVE.value
        and moat != MoatStatus.DETERIORATING.value
        and rsi is not None
        and rsi < RSI_CONTRARIAN_BUY_THRESHOLD
    ):
        return ScanSignal.CONTRARIAN_BUY

    if bias is not None and bias > BIAS_OVERHEATED_THRESHOLD:
        return ScanSignal.OVERHEATED

    return ScanSignal.NORMAL


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


# 各等級對應的 0–100 分數中心值（用於 VIX 等級→分數轉換）
_LEVEL_SCORE: dict[FearGreedLevel, int] = {
    FearGreedLevel.EXTREME_FEAR: 10,
    FearGreedLevel.FEAR: 30,
    FearGreedLevel.NEUTRAL: 50,
    FearGreedLevel.GREED: 70,
    FearGreedLevel.EXTREME_GREED: 90,
    FearGreedLevel.NOT_AVAILABLE: 50,  # fallback
}


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
    綜合 VIX 與 CNN Fear & Greed Index 計算複合恐懼貪婪等級與分數。
    VIX 權重 40%，CNN 權重 60%。若 CNN 不可用，100% 使用 VIX。
    回傳 (等級, 0–100 分數)。
    純函式，無副作用。
    """
    vix_score = _vix_to_score(vix_value) if vix_value is not None else None

    if vix_score is not None and cnn_score is not None:
        composite = round(vix_score * FG_WEIGHT_VIX + cnn_score * FG_WEIGHT_CNN)
    elif vix_score is not None:
        composite = vix_score
    elif cnn_score is not None:
        composite = cnn_score
    else:
        return FearGreedLevel.NOT_AVAILABLE, 50

    composite = max(0, min(100, composite))
    level = classify_cnn_fear_greed(composite)
    return level, composite
