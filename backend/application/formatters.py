"""
Application — 表示層格式化函式。
將原始數值資料轉換為使用者可讀的狀態文字。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from domain.withdrawal import WithdrawalPlan

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    BIAS_OVERSOLD_THRESHOLD,
    MA200_WINDOW,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
)
from i18n import t


def build_signal_status(signals: dict, lang: str = "zh-TW") -> list[str]:
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
            status_parts.append(t("formatter.rsi_oversold", lang=lang, rsi=rsi))
        elif rsi > RSI_OVERBOUGHT:
            status_parts.append(t("formatter.rsi_overbought", lang=lang, rsi=rsi))
        else:
            status_parts.append(t("formatter.rsi_neutral", lang=lang, rsi=rsi))

    if ma200 is not None:
        if price is not None and price < ma200:
            status_parts.append(
                t("formatter.price_below_ma200", lang=lang, price=price, ma200=ma200)
            )
        else:
            status_parts.append(
                t("formatter.price_above_ma200", lang=lang, price=price, ma200=ma200)
            )
    else:
        status_parts.append(
            t("formatter.insufficient_data_ma200", lang=lang, days=MA200_WINDOW)
        )

    if ma60 is not None:
        if price is not None and price < ma60:
            status_parts.append(
                t("formatter.price_below_ma60", lang=lang, price=price, ma60=ma60)
            )
        else:
            status_parts.append(
                t("formatter.price_above_ma60", lang=lang, price=price, ma60=ma60)
            )

    if bias is not None:
        if bias > BIAS_OVERHEATED_THRESHOLD:
            status_parts.append(t("formatter.bias_overheated", lang=lang, bias=bias))
        elif bias < BIAS_OVERSOLD_THRESHOLD:
            status_parts.append(t("formatter.bias_oversold", lang=lang, bias=bias))

    return status_parts


def build_moat_details(
    moat_status_value: str,
    current_margin: Optional[float],
    previous_margin: Optional[float],
    change: float,
    lang: str = "zh-TW",
) -> str:
    """
    根據護城河判定結果，產生使用者可讀的詳情文字。
    """
    from domain.enums import MoatStatus

    if moat_status_value == MoatStatus.DETERIORATING.value:
        return t(
            "formatter.moat_deteriorating",
            lang=lang,
            current=current_margin,
            previous=previous_margin,
            change=abs(change),
        )
    return t(
        "formatter.moat_stable",
        lang=lang,
        current=current_margin,
        previous=previous_margin,
        sign="+" if change >= 0 else "",
        change=change,
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


def format_fear_greed_label(level: str, score: int, lang: str = "zh-TW") -> str:
    """
    格式化恐懼與貪婪等級為標籤（含 icon 與分數）。
    例如：「😱 極度恐慌（15）」
    """
    label_key = f"formatter.fear_greed_{level.lower()}"
    label = t(label_key, score=score, lang=lang)
    return label


def format_fear_greed_short(level: str, lang: str = "zh-TW") -> str:
    """
    格式化恐懼與貪婪等級為精簡標籤（icon + 文字）。
    例如：「😱 極度恐懼」
    """
    icon = _FEAR_GREED_ICON.get(level, "⏳")
    label_key = f"formatter.fear_greed_{level.lower()}"
    label = t(label_key, lang=lang)
    return f"{icon} {label}"


# ---------------------------------------------------------------------------
# 聰明提款格式化
# ---------------------------------------------------------------------------


def format_withdrawal_telegram(
    plan: WithdrawalPlan, display_currency: str = "USD", lang: str = "zh-TW"
) -> str:
    """
    將 WithdrawalPlan 格式化為 Telegram HTML 訊息。

    Args:
        plan: domain.withdrawal.WithdrawalPlan 實例
        display_currency: 顯示幣別
        lang: 語言代碼

    Returns:
        Telegram HTML 格式訊息字串
    """
    from domain.constants import CATEGORY_ICON

    parts: list[str] = [
        t(
            "formatter.withdrawal_header",
            lang=lang,
            amount=f"{plan.target_amount:,.2f}",
            currency=display_currency,
        ),
    ]

    if not plan.recommendations:
        parts.append(t("formatter.withdrawal_no_holdings", lang=lang))
        return "\n".join(parts)

    parts.append(t("formatter.withdrawal_recommendations", lang=lang))
    for i, rec in enumerate(plan.recommendations, 1):
        icon = CATEGORY_ICON.get(rec.category, "📊")
        pl_text = ""
        if rec.unrealized_pl is not None:
            pl_sign = "+" if rec.unrealized_pl >= 0 else ""
            pl_text = t(
                "formatter.withdrawal_pl",
                lang=lang,
                sign=pl_sign,
                amount=f"{rec.unrealized_pl:,.2f}",
                currency=display_currency,
            )
        priority_label = t(
            f"formatter.priority_{['rebalance', 'tax', 'liquidity'][rec.priority - 1]}",
            lang=lang,
        )
        parts.append(
            f"\n{i}. {icon} <b>{rec.ticker}</b> ({rec.category})"
            f" — {t('formatter.sell', lang=lang)} {rec.quantity_to_sell:,.4g} "
            f"{t('formatter.shares', lang=lang)}"
            f"（{rec.sell_value:,.2f} {display_currency}）"
            f"\n   {t('formatter.reason', lang=lang)}：{rec.reason}"
            f"\n   {t('formatter.priority', lang=lang)}：{priority_label}"
            f"{pl_text}"
        )

    parts.append(
        t(
            "formatter.withdrawal_total",
            lang=lang,
            amount=f"{plan.total_sell_value:,.2f}",
            currency=display_currency,
        )
    )

    if plan.shortfall > 0:
        parts.append(
            t(
                "formatter.withdrawal_shortfall",
                lang=lang,
                amount=f"{plan.shortfall:,.2f}",
                currency=display_currency,
            )
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Smart Money (大師足跡) 格式化
# ---------------------------------------------------------------------------


_HOLDING_ACTION_ICON: dict[str, str] = {
    "NEW_POSITION": "🟢",
    "SOLD_OUT": "🔴",
    "INCREASED": "📈",
    "DECREASED": "📉",
    "UNCHANGED": "⚪",
}


def format_guru_filing_digest(summaries: list[dict], lang: str = "zh-TW") -> str:
    """
    將多位大師的 13F 季報摘要格式化為 Telegram HTML 訊息。

    Args:
        summaries: list of filing summary dicts（來自 filing_service，需包含
                   guru_display_name, report_date, new_positions, sold_out,
                   increased, decreased, top_holdings）
        lang: 語言代碼

    Returns:
        Telegram HTML 格式字串
    """
    if not summaries:
        return t("guru.digest_no_updates", lang=lang)

    report_date = summaries[0].get("report_date", "")
    parts: list[str] = [
        t("guru.filing_digest_title", lang=lang, report_date=report_date),
        "",
    ]

    for summary in summaries:
        name = summary.get("guru_display_name", "")
        new_pos = summary.get("new_positions", 0)
        sold = summary.get("sold_out", 0)
        increased = summary.get("increased", 0)
        decreased = summary.get("decreased", 0)

        parts.append(f"<b>{name}</b>")
        if new_pos or sold or increased or decreased:
            parts.append(
                t(
                    "guru.digest_changes",
                    lang=lang,
                    new=new_pos,
                    sold=sold,
                    inc=increased,
                    dec=decreased,
                )
            )
        else:
            parts.append(t("guru.digest_no_changes", lang=lang))

        # Top 3 holdings for brevity
        for h in summary.get("top_holdings", [])[:3]:
            icon = _HOLDING_ACTION_ICON.get(h.get("action", ""), "⚪")
            ticker = h.get("ticker") or h.get("cusip", "")
            weight = h.get("weight_pct") or 0.0
            parts.append(f"  {icon} {ticker} ({weight:.1f}%)")
        parts.append("")

    parts.append(t("guru.lagging_disclaimer_short", lang=lang))
    return "\n".join(parts)


def format_resonance_alert(
    ticker: str, guru_name: str, action: str, lang: str = "zh-TW"
) -> str:
    """
    格式化單一共鳴警報：大師對使用者關注清單中的股票進行了操作。

    Args:
        ticker: 股票代號
        guru_name: 大師顯示名稱
        action: HoldingAction value（e.g. "NEW_POSITION"）
        lang: 語言代碼

    Returns:
        Telegram HTML 格式字串
    """
    icon = _HOLDING_ACTION_ICON.get(action, "⚪")
    action_label = t(f"guru.action_{action.lower()}", lang=lang)
    return t(
        "guru.resonance_alert",
        lang=lang,
        icon=icon,
        guru_name=guru_name,
        action=action_label,
        ticker=ticker,
    )
