"""
Domain — 匯率變動分析純函式。
不依賴任何外部服務、資料庫或框架。
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.constants import (
    FX_DAILY_SPIKE_PCT,
    FX_LONG_TERM_TREND_PCT,
    FX_SHORT_TERM_SWING_PCT,
)
from domain.enums import FXAlertType


@dataclass(frozen=True)
class FXRateAlert:
    """單一匯率變動警報。"""

    pair: str  # e.g. "USD/TWD"
    alert_type: FXAlertType
    change_pct: float  # signed percentage change
    direction: str  # "up" / "down"
    current_rate: float
    period_label: str  # "1 日" / "5 日" / "3 個月"


def _compute_change_pct(
    history: list[dict],
    start_idx: int = 0,
    end_idx: int = -1,
) -> float | None:
    """
    從 history[start_idx] 到 history[end_idx] 計算百分比變動。
    history 格式: [{"date": "...", "close": float}, ...]
    回傳 signed percentage; 若資料不足回傳 None。
    """
    if not history or len(history) < 2:
        return None
    first = history[start_idx]["close"]
    last = history[end_idx]["close"]
    if first <= 0:
        return None
    return round(((last - first) / first) * 100, 2)


def _direction(pct: float) -> str:
    return "up" if pct > 0 else ("down" if pct < 0 else "flat")


def analyze_fx_rate_changes(
    pair: str,
    current_rate: float,
    short_history: list[dict],
    long_history: list[dict],
) -> list[FXRateAlert]:
    """
    分析單一貨幣對的匯率變動，偵測三種警報：

    1. Daily spike: 最近一日 vs 前一日 > FX_DAILY_SPIKE_PCT
    2. Short-term swing: 5 日首尾 > FX_SHORT_TERM_SWING_PCT
    3. Long-term trend: 3 月首尾 > FX_LONG_TERM_TREND_PCT

    純函式，不依賴外部狀態。
    """
    alerts: list[FXRateAlert] = []

    # 1) Daily spike: last two data points in short_history
    if len(short_history) >= 2:
        daily_pct = _compute_change_pct(short_history, -2, -1)
        if daily_pct is not None and abs(daily_pct) >= FX_DAILY_SPIKE_PCT:
            alerts.append(
                FXRateAlert(
                    pair=pair,
                    alert_type=FXAlertType.DAILY_SPIKE,
                    change_pct=daily_pct,
                    direction=_direction(daily_pct),
                    current_rate=current_rate,
                    period_label="1 日",
                )
            )

    # 2) Short-term swing: first to last in short_history
    if len(short_history) >= 2:
        swing_pct = _compute_change_pct(short_history, 0, -1)
        if swing_pct is not None and abs(swing_pct) >= FX_SHORT_TERM_SWING_PCT:
            alerts.append(
                FXRateAlert(
                    pair=pair,
                    alert_type=FXAlertType.SHORT_TERM_SWING,
                    change_pct=swing_pct,
                    direction=_direction(swing_pct),
                    current_rate=current_rate,
                    period_label="5 日",
                )
            )

    # 3) Long-term trend: first to last in long_history
    if len(long_history) >= 2:
        trend_pct = _compute_change_pct(long_history, 0, -1)
        if trend_pct is not None and abs(trend_pct) >= FX_LONG_TERM_TREND_PCT:
            alerts.append(
                FXRateAlert(
                    pair=pair,
                    alert_type=FXAlertType.LONG_TERM_TREND,
                    change_pct=trend_pct,
                    direction=_direction(trend_pct),
                    current_rate=current_rate,
                    period_label="3 個月",
                )
            )

    return alerts


def determine_fx_risk_level(all_alerts: list[FXRateAlert]) -> str:
    """
    根據觸發的警報類型決定整體匯率風險等級。

    - 含 daily_spike => "high"
    - 含 short_term_swing => "medium"
    - 其他 => "low"
    """
    alert_types = {a.alert_type for a in all_alerts}
    if FXAlertType.DAILY_SPIKE in alert_types:
        return "high"
    if FXAlertType.SHORT_TERM_SWING in alert_types:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# FX Exchange Timing Analysis
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FXTimingResult:
    """換匯時機分析結果。"""

    base_currency: str  # e.g. "USD"
    quote_currency: str  # e.g. "TWD"
    current_rate: float
    is_recent_high: bool  # 是否接近近期高點
    lookback_high: float  # 回溯期間最高價
    lookback_days: int  # 回溯天數
    consecutive_increases: int  # 連續上漲天數
    consecutive_threshold: int  # 連續上漲門檻
    alert_on_recent_high: bool  # 是否啟用近期高點警報
    alert_on_consecutive_increase: bool  # 是否啟用連續上漲警報
    should_alert: bool  # 是否應發出警報
    recommendation_zh: str  # 繁體中文建議
    reasoning_zh: str  # 繁體中文理由


def is_recent_high(
    current_rate: float,
    history: list[dict],
    lookback_days: int,
    tolerance_pct: float = 2.0,
) -> tuple[bool, float]:
    """
    判斷當前匯率是否接近近期高點。

    Args:
        current_rate: 當前匯率
        history: 歷史資料 [{\"date\": \"...\", \"close\": float}, ...]
        lookback_days: 回溯天數
        tolerance_pct: 容忍百分比（預設 2%，即 98% 以上視為近期高點）

    Returns:
        (是否接近高點, 期間最高價)
    """
    if not history:
        return False, 0.0

    # 取最近 N 天資料（若資料不足則取所有可用資料）
    recent = history[-lookback_days:] if len(history) >= lookback_days else history
    high = max(d["close"] for d in recent)

    if high <= 0:
        return False, 0.0

    # 當前價格達到期間高點的 (100 - tolerance_pct)% 以上
    threshold = high * (1.0 - tolerance_pct / 100.0)
    return current_rate >= threshold, high


def count_consecutive_increases(history: list[dict]) -> int:
    """
    計算歷史資料中最後連續上漲的天數。

    Args:
        history: 歷史資料 [{\"date\": \"...\", \"close\": float}, ...]

    Returns:
        連續上漲天數（從最後一天往前計算）
    """
    if len(history) < 2:
        return 0

    count = 0
    for i in range(len(history) - 1, 0, -1):
        if history[i]["close"] > history[i - 1]["close"]:
            count += 1
        else:
            break
    return count


def assess_exchange_timing(
    base_currency: str,
    quote_currency: str,
    history: list[dict],
    recent_high_days: int,
    consecutive_threshold: int,
    alert_on_recent_high: bool = True,
    alert_on_consecutive_increase: bool = True,
) -> FXTimingResult:
    """
    評估換匯時機，產出結構化分析結果。

    Args:
        base_currency: 基礎貨幣（例如 USD）
        quote_currency: 報價貨幣（例如 TWD）
        history: 歷史匯率資料 [{\"date\": \"...\", \"close\": float}, ...]
        recent_high_days: 回溯天數（近期高點判定）
        consecutive_threshold: 連續上漲天數門檻
        alert_on_recent_high: 是否啟用近期高點警報（預設 True）
        alert_on_consecutive_increase: 是否啟用連續上漲警報（預設 True）

    Returns:
        FXTimingResult 結構化分析結果
    """
    if not history:
        return FXTimingResult(
            base_currency=base_currency,
            quote_currency=quote_currency,
            current_rate=0.0,
            is_recent_high=False,
            lookback_high=0.0,
            lookback_days=recent_high_days,
            consecutive_increases=0,
            consecutive_threshold=consecutive_threshold,
            alert_on_recent_high=alert_on_recent_high,
            alert_on_consecutive_increase=alert_on_consecutive_increase,
            should_alert=False,
            recommendation_zh="無歷史資料，無法分析",
            reasoning_zh="歷史資料不足",
        )

    current_rate = history[-1]["close"]
    near_high, high = is_recent_high(current_rate, history, recent_high_days)
    consec = count_consecutive_increases(history)

    # 判斷是否應發出警報：根據啟用的條件使用 OR 邏輯
    if not alert_on_recent_high and not alert_on_consecutive_increase:
        # 兩項條件皆關閉
        should_alert = False
        recommendation_zh = "監控已停用：兩項條件皆關閉"
        reasoning_zh = "請啟用至少一項警報條件（近期高點或連續上漲）"
    else:
        # 評估啟用的條件
        high_condition = alert_on_recent_high and near_high
        consec_condition = alert_on_consecutive_increase and consec >= consecutive_threshold
        should_alert = high_condition or consec_condition

        if should_alert:
            # 產生觸發條件說明
            triggers = []
            if high_condition and consec_condition:
                triggers.append("近期高點 + 連續上漲")
            elif high_condition:
                triggers.append("近期高點")
            elif consec_condition:
                triggers.append("連續上漲")

            recommendation_zh = (
                f"建議考慮換匯：{base_currency} → {quote_currency}（{'、'.join(triggers)}）"
            )
            parts = []
            if high_condition:
                parts.append(f"已接近 {recent_high_days} 日高點 ({high:.4f})")
            if consec_condition:
                parts.append(f"連續上漲 {consec} 日")
            reasoning_zh = (
                f"{base_currency}/{quote_currency} "
                f"{'，且'.join(parts)}，現在可能是換匯好時機。"
            )
        elif near_high and not alert_on_consecutive_increase:
            # 偵測到高點但連續上漲監控已關閉
            recommendation_zh = "接近高點（連續上漲監控已關閉）"
            reasoning_zh = f"匯率接近 {recent_high_days} 日高點，連續上漲監控未啟用。"
        elif near_high and alert_on_consecutive_increase:
            # 接近高點但連續上漲未達標
            recommendation_zh = "接近高點但上漲動能不足，可再觀察"
            reasoning_zh = (
                f"匯率接近 {recent_high_days} 日高點，但連續上漲僅 {consec} 日 "
                f"(門檻 {consecutive_threshold} 日)，建議再觀察。"
            )
        elif consec >= consecutive_threshold and not alert_on_recent_high:
            # 連續上漲達標但近期高點監控已關閉
            recommendation_zh = "持續上漲（近期高點監控已關閉）"
            reasoning_zh = f"連續上漲 {consec} 日達門檻，近期高點監控未啟用。"
        elif consec >= consecutive_threshold and alert_on_recent_high:
            # 連續上漲達標但未達高點
            recommendation_zh = "持續上漲但未達高點，可再等待"
            reasoning_zh = (
                f"連續上漲 {consec} 日但匯率尚未達 {recent_high_days} 日高點附近，"
                f"可能還有上漲空間。"
            )
        else:
            recommendation_zh = "暫無換匯訊號"
            reasoning_zh = f"匯率未達近期高點，且連續上漲僅 {consec} 日。"

    return FXTimingResult(
        base_currency=base_currency,
        quote_currency=quote_currency,
        current_rate=current_rate,
        is_recent_high=near_high,
        lookback_high=high,
        lookback_days=recent_high_days,
        consecutive_increases=consec,
        consecutive_threshold=consecutive_threshold,
        alert_on_recent_high=alert_on_recent_high,
        alert_on_consecutive_increase=alert_on_consecutive_increase,
        should_alert=should_alert,
        recommendation_zh=recommendation_zh,
        reasoning_zh=reasoning_zh,
    )
