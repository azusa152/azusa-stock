"""
Domain — 純格式化函式（無副作用，僅依賴 domain 常數與 i18n）。
將原始數值資料轉換為使用者可讀的狀態文字。
"""

from __future__ import annotations

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
    current_margin: float | None,
    previous_margin: float | None,
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
