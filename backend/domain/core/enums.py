"""
Domain — 列舉定義。
業務規則中使用的分類與狀態常數。
"""

from enum import StrEnum
from typing import NewType

# I18nKey is a str that holds an i18n lookup key (e.g. "fx.period_1d").
# The application layer is responsible for translating it with t(key, lang=lang).
# Using NewType makes the distinction explicit in type annotations without runtime cost.
I18nKey = NewType("I18nKey", str)


class StockCategory(StrEnum):
    """股票分類：風向球 / 護城河 / 成長夢想 / 債券 / 現金"""

    TREND_SETTER = "Trend_Setter"
    MOAT = "Moat"
    GROWTH = "Growth"
    BOND = "Bond"
    CASH = "Cash"


class MoatStatus(StrEnum):
    """護城河趨勢狀態"""

    DETERIORATING = "DETERIORATING"
    STABLE = "STABLE"
    NOT_AVAILABLE = "N/A"


class MarketSentiment(StrEnum):
    """市場情緒判定（5 階段，基於風向球跌破 60MA 之比例）"""

    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class ScanSignal(StrEnum):
    """掃描決策訊號"""

    THESIS_BROKEN = "THESIS_BROKEN"
    DEEP_VALUE = "DEEP_VALUE"
    OVERSOLD = "OVERSOLD"
    CONTRARIAN_BUY = "CONTRARIAN_BUY"
    APPROACHING_BUY = "APPROACHING_BUY"
    OVERHEATED = "OVERHEATED"
    CAUTION_HIGH = "CAUTION_HIGH"
    WEAKENING = "WEAKENING"
    NORMAL = "NORMAL"


class FearGreedLevel(StrEnum):
    """恐懼與貪婪指數等級（VIX + CNN Fear & Greed 綜合）"""

    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"
    NOT_AVAILABLE = "N/A"


FEAR_GREED_LABEL: dict[str, str] = {
    "EXTREME_FEAR": "極度恐懼",
    "FEAR": "恐懼",
    "NEUTRAL": "中性",
    "GREED": "貪婪",
    "EXTREME_GREED": "極度貪婪",
    "N/A": "無資料",
}


CATEGORY_LABEL: dict[str, str] = {
    "Trend_Setter": "風向球",
    "Moat": "護城河",
    "Growth": "成長夢想",
    "Bond": "債券",
    "Cash": "現金",
}


class FXAlertType(StrEnum):
    """匯率變動警報類型"""

    DAILY_SPIKE = "daily_spike"
    SHORT_TERM_SWING = "short_term_swing"
    LONG_TERM_TREND = "long_term_trend"


# Values are i18n keys, resolved via t() in the application layer.
FX_ALERT_LABEL: dict[str, str] = {
    "daily_spike": "fx.alert_type_daily_spike",
    "short_term_swing": "fx.alert_type_short_term_swing",
    "long_term_trend": "fx.alert_type_long_term_trend",
}


class HoldingAction(StrEnum):
    """大師持倉的變動類型"""

    NEW_POSITION = "NEW_POSITION"  # 本季新建倉
    SOLD_OUT = "SOLD_OUT"  # 本季清倉
    INCREASED = "INCREASED"  # 加碼 (>= threshold)
    DECREASED = "DECREASED"  # 減碼 (>= threshold)
    UNCHANGED = "UNCHANGED"  # 持平 (< threshold)


class GuruStyle(StrEnum):
    """大師投資風格分類（基於 HFR 行業標準分類）。"""

    VALUE = "VALUE"
    GROWTH = "GROWTH"
    MACRO = "MACRO"
    QUANT = "QUANT"
    ACTIVIST = "ACTIVIST"
    MULTI_STRATEGY = "MULTI_STRATEGY"


class GuruTier(StrEnum):
    """大師等級排名（編輯評選，非基於績效計算）。"""

    TIER_1 = "TIER_1"  # 傳奇 / 必追蹤
    TIER_2 = "TIER_2"  # 菁英 / 高關注度
    TIER_3 = "TIER_3"  # 值得關注 / 利基 / 使用者自訂
