"""
Domain — Smart Money Tracker 純函數。
無任何外部依賴，所有業務邏輯可單獨測試。
"""

from domain.constants import GURU_HOLDING_CHANGE_THRESHOLD_PCT
from domain.enums import HoldingAction


def classify_holding_change(
    current_shares: float,
    previous_shares: float | None,
    threshold_pct: float = GURU_HOLDING_CHANGE_THRESHOLD_PCT,
) -> HoldingAction:
    """判斷大師持倉的變動類型。

    Args:
        current_shares: 本季持股數量。
        previous_shares: 前季持股數量；None 表示前季無持倉。
        threshold_pct: 判定加碼／減碼的最小變動百分比門檻（含）。

    Returns:
        HoldingAction 枚舉值。
    """
    if previous_shares is None or previous_shares == 0.0:
        if current_shares > 0:
            return HoldingAction.NEW_POSITION
        return HoldingAction.UNCHANGED

    if current_shares == 0.0:
        return HoldingAction.SOLD_OUT

    change = compute_change_pct(current_shares, previous_shares)
    if change is None:
        return HoldingAction.UNCHANGED

    if change >= threshold_pct:
        return HoldingAction.INCREASED
    if change <= -threshold_pct:
        return HoldingAction.DECREASED
    return HoldingAction.UNCHANGED


def compute_change_pct(
    current: float,
    previous: float,
) -> float | None:
    """計算持股數量的百分比變動。

    Args:
        current: 本季持股數量。
        previous: 前季持股數量。

    Returns:
        變動百分比（正為增加，負為減少），若 previous 為 0 則回傳 None。
    """
    if previous == 0.0:
        return None
    return round((current - previous) / previous * 100, 2)


def compute_holding_weight(holding_value: float, total_value: float) -> float:
    """計算單一持倉佔總持倉的百分比權重。

    Args:
        holding_value: 單一持倉市值。
        total_value: 全部持倉總市值。

    Returns:
        百分比權重（0.0 ~ 100.0）；若 total_value 為 0 則回傳 0.0。
    """
    if total_value == 0.0:
        return 0.0
    return round(holding_value / total_value * 100, 2)


def compute_resonance_matches(
    guru_tickers: set[str],
    user_tickers: set[str],
) -> set[str]:
    """計算大師持倉與使用者關注清單／持倉的重疊股票。

    Args:
        guru_tickers: 大師當季持倉的股票代號集合。
        user_tickers: 使用者追蹤清單或實際持倉的股票代號集合。

    Returns:
        兩者的交集（共鳴股票）。
    """
    return guru_tickers & user_tickers
