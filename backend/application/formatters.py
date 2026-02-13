"""
Application — 表示層格式化函式。
將原始數值資料轉換為使用者可讀的狀態文字。
"""

from typing import Optional

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    BIAS_OVERSOLD_THRESHOLD,
    MA200_WINDOW,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
)


def build_signal_status(signals: dict) -> list[str]:
    """
    根據原始技術訊號數值，產生使用者可讀的狀態描述列表。
    """
    status_parts: list[str] = []

    rsi = signals.get("rsi")
    price = signals.get("price")
    ma200 = signals.get("ma200")
    ma60 = signals.get("ma60")
    bias = signals.get("bias")

    if rsi is not None:
        if rsi < RSI_OVERSOLD:
            status_parts.append(f"🟢 RSI={rsi} 超賣區間（可能是機會）")
        elif rsi > RSI_OVERBOUGHT:
            status_parts.append(f"🔴 RSI={rsi} 超買區間（留意回檔）")
        else:
            status_parts.append(f"⚪ RSI={rsi} 中性")

    if ma200 is not None:
        if price is not None and price < ma200:
            status_parts.append(f"🔴 股價 {price} 跌破 200MA ({ma200})")
        else:
            status_parts.append(f"🟢 股價 {price} 站穩 200MA ({ma200})")
    else:
        status_parts.append(f"⚠️ 資料不足 {MA200_WINDOW} 天，無法計算 200MA")

    if ma60 is not None:
        if price is not None and price < ma60:
            status_parts.append(f"🔴 股價 {price} 跌破 60MA ({ma60})")
        else:
            status_parts.append(f"🟢 股價 {price} 站穩 60MA ({ma60})")

    if bias is not None:
        if bias > BIAS_OVERHEATED_THRESHOLD:
            status_parts.append(f"🔴 乖離率 {bias}% 過熱")
        elif bias < BIAS_OVERSOLD_THRESHOLD:
            status_parts.append(f"🟢 乖離率 {bias}% 超跌")

    return status_parts


def build_moat_details(
    moat_status_value: str,
    current_margin: Optional[float],
    previous_margin: Optional[float],
    change: float,
) -> str:
    """
    根據護城河判定結果，產生使用者可讀的詳情文字。
    """
    from domain.enums import MoatStatus

    if moat_status_value == MoatStatus.DETERIORATING.value:
        return (
            f"毛利率衰退！{current_margin}% → 去年同期 {previous_margin}%"
            f"（下降 {abs(change)} 個百分點）— 護城河鬆動！"
        )
    return (
        f"毛利率穩健：{current_margin}% vs 去年同期 {previous_margin}%"
        f"（{'+' if change >= 0 else ''}{change} 個百分點）"
    )


# ---------------------------------------------------------------------------
# 恐懼與貪婪指數格式化
# ---------------------------------------------------------------------------

_FEAR_GREED_ICON: dict[str, str] = {
    "EXTREME_FEAR": "😱",
    "FEAR": "😨",
    "NEUTRAL": "😐",
    "GREED": "🤑",
    "EXTREME_GREED": "🤯",
    "N/A": "⏳",
}

_FEAR_GREED_LABEL_ZH: dict[str, str] = {
    "EXTREME_FEAR": "極度恐懼",
    "FEAR": "恐懼",
    "NEUTRAL": "中性",
    "GREED": "貪婪",
    "EXTREME_GREED": "極度貪婪",
    "N/A": "無資料",
}


def format_fear_greed_label(level: str, score: int) -> str:
    """
    格式化恐懼與貪婪等級為繁體中文標籤（含 icon 與分數）。
    例如：「😱 極度恐懼 (15)」
    """
    icon = _FEAR_GREED_ICON.get(level, "⏳")
    label = _FEAR_GREED_LABEL_ZH.get(level, "無資料")
    return f"{icon} {label} ({score})"


def format_fear_greed_short(level: str) -> str:
    """
    格式化恐懼與貪婪等級為精簡標籤（icon + 中文）。
    例如：「😱 極度恐懼」
    """
    icon = _FEAR_GREED_ICON.get(level, "⏳")
    label = _FEAR_GREED_LABEL_ZH.get(level, "無資料")
    return f"{icon} {label}"


# ---------------------------------------------------------------------------
# 聰明提款格式化
# ---------------------------------------------------------------------------

_PRIORITY_LABEL: dict[int, str] = {
    1: "再平衡",
    2: "節稅",
    3: "流動性",
}


def format_withdrawal_telegram(
    plan: "WithdrawalPlan", display_currency: str = "USD"
) -> str:  # noqa: F821
    """
    將 WithdrawalPlan 格式化為 Telegram HTML 訊息。

    Args:
        plan: domain.withdrawal.WithdrawalPlan 實例
        display_currency: 顯示幣別

    Returns:
        Telegram HTML 格式訊息字串
    """
    from domain.constants import CATEGORY_ICON

    parts: list[str] = [
        f"🏧 <b>聰明提款建議</b>（目標：{plan.target_amount:,.2f} {display_currency}）\n",
    ]

    if not plan.recommendations:
        parts.append("⚠️ 無可賣出的持倉。")
        return "\n".join(parts)

    parts.append("📋 <b>建議賣出：</b>")
    for i, rec in enumerate(plan.recommendations, 1):
        icon = CATEGORY_ICON.get(rec.category, "📊")
        pl_text = ""
        if rec.unrealized_pl is not None:
            pl_sign = "+" if rec.unrealized_pl >= 0 else ""
            pl_text = f"\n   損益：{pl_sign}{rec.unrealized_pl:,.2f} {display_currency}"
        priority_label = _PRIORITY_LABEL.get(rec.priority, "其他")
        parts.append(
            f"\n{i}. {icon} <b>{rec.ticker}</b> ({rec.category})"
            f" — 賣出 {rec.quantity_to_sell:,.4g} 股"
            f"（{rec.sell_value:,.2f} {display_currency}）"
            f"\n   理由：{rec.reason}"
            f"\n   優先級：{priority_label}"
            f"{pl_text}"
        )

    parts.append(f"\n💰 總賣出金額：{plan.total_sell_value:,.2f} {display_currency}")

    if plan.shortfall > 0:
        parts.append(f"⚠️ 持倉不足，缺口：{plan.shortfall:,.2f} {display_currency}")

    return "\n".join(parts)
