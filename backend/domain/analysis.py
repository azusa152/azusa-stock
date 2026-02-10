"""
Domain — 純粹的分析計算函式。
不依賴任何外部服務、資料庫或框架，僅接收資料並回傳結果。
可獨立測試。
"""

from typing import Optional

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    MARKET_CAUTION_BELOW_60MA_PCT,
    MOAT_MARGIN_DETERIORATION_THRESHOLD,
    RSI_CONTRARIAN_BUY_THRESHOLD,
    VOLUME_RATIO_LONG_DAYS,
    VOLUME_RATIO_SHORT_DAYS,
)
from domain.enums import MarketSentiment, MoatStatus, ScanSignal


# ---------------------------------------------------------------------------
# 技術指標計算
# ---------------------------------------------------------------------------


def compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
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
