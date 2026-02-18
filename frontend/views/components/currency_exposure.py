"""
Folio — Currency Exposure Component (匯率曝險監控).
Reusable component for rendering Step 4: FX donut charts, movements, alerts, and advice.
"""

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    DISPLAY_CURRENCY_OPTIONS,
    PRIVACY_MASK,
)
from i18n import t
from utils import (
    api_put,
    fetch_currency_exposure,
    format_utc_timestamp,
    invalidate_profile_caches,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    post_fx_exposure_alert,
    show_toast,
)


# ---------------------------------------------------------------------------
# Constants (moved from allocation.py — only used by this component)
# ---------------------------------------------------------------------------

_CUR_COLORS = {
    "USD": "#3B82F6",
    "TWD": "#10B981",
    "JPY": "#F59E0B",
    "EUR": "#8B5CF6",
    "GBP": "#EF4444",
    "CNY": "#EC4899",
    "HKD": "#F97316",
    "SGD": "#14B8A6",
    "THB": "#6366F1",
}

_RISK_COLORS = {"low": "🟢", "medium": "🟡", "high": "🔴"}

def _get_risk_label(risk_level: str) -> str:
    """Get localized risk label."""
    return t(f"components.currency.risk.{risk_level}")

_ALERT_TYPE_BADGES = {
    "daily_spike": ("🔴", lambda: t("components.currency.alert_type.daily_spike")),
    "short_term_swing": ("🟡", lambda: t("components.currency.alert_type.short_term_swing")),
    "long_term_trend": ("🔵", lambda: t("components.currency.alert_type.long_term_trend")),
}

# Regex: match numeric amounts followed by a currency code
_CURRENCY_AMOUNT_RE = re.compile(
    r"[\d,]+(?:\.\d+)?(?=\s*(?:TWD|USD|JPY|EUR|GBP|CNY|HKD|SGD|THB))"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_currency_exposure(
    profile: dict,
    holdings: list[dict],
    display_cur: str = "USD",
) -> None:
    """Render Step 4 — Currency Exposure Monitor.

    Includes FX data fetch, home currency selector, donut charts,
    movements table, rate alerts, and advice for cash and total tabs.

    Args:
        profile: Current user profile (used for home_currency update).
        holdings: Current holdings list (reserved for future use).
        display_cur: Display currency from rebalance (reserved for future use).
    """
    with st.status(
        t("components.currency.loading"), expanded=True
    ) as _fx_status:
        fx_data = fetch_currency_exposure()
        if fx_data:
            _fx_status.update(
                label=t("components.currency.loaded"),
                state="complete",
                expanded=False,
            )
        else:
            _fx_status.update(
                label=t("components.currency.error"),
                state="error",
                expanded=True,
            )

    if not fx_data:
        return

    fx_calc_at = fx_data.get("calculated_at", "")
    fx_home = fx_data.get("home_currency", "TWD")

    # --- Home currency selector (inline in Step 4) ---
    _fx_hdr_cols = st.columns([3, 1])
    with _fx_hdr_cols[0]:
        if fx_calc_at:
            browser_tz = st.session_state.get("browser_tz")
            st.caption(
                t("components.currency.analysis_time", time=format_utc_timestamp(fx_calc_at, browser_tz))
            )
    with _fx_hdr_cols[1]:
        _fx_cur_idx = (
            DISPLAY_CURRENCY_OPTIONS.index(fx_home)
            if fx_home in DISPLAY_CURRENCY_OPTIONS
            else 0
        )
        new_fx_home = st.selectbox(
            t("components.currency.home_currency"),
            options=DISPLAY_CURRENCY_OPTIONS,
            index=_fx_cur_idx,
            key="fx_home_currency_selector",
        )
        if new_fx_home != fx_home and profile and profile.get("id"):
            result = api_put(
                f"/profiles/{profile['id']}",
                {"home_currency": new_fx_home},
            )
            if result:
                invalidate_profile_caches()
                st.rerun()

    # --- Shared data ---
    fx_movements = fx_data.get("fx_movements", [])

    # --- Two tabs: Cash vs Total ---
    fx_tab_cash, fx_tab_total = st.tabs(
        [t("components.currency.tab.cash"), t("components.currency.tab.total")]
    )

    with fx_tab_cash:
        _render_cash_tab(fx_data, fx_home, fx_movements)

    with fx_tab_total:
        _render_total_tab(fx_data, fx_home, fx_movements)


# ---------------------------------------------------------------------------
# Private renderers
# ---------------------------------------------------------------------------


def _render_cash_tab(
    fx_data: dict, fx_home: str, fx_movements: list[dict]
) -> None:
    """Render the cash currency exposure tab."""
    cash_bd = fx_data.get("cash_breakdown", [])
    cash_nhp = fx_data.get("cash_non_home_pct", 0.0)
    total_cash = fx_data.get("total_cash_home", 0.0)

    if not cash_bd:
        st.info(t("components.currency.no_cash"))
        return

    cash_risk = fx_data.get("risk_level", "low")

    cash_m_cols = st.columns(3)
    with cash_m_cols[0]:
        st.metric(
            t("components.currency.cash_total", currency=fx_home),
            _mask_money(total_cash),
        )
    with cash_m_cols[1]:
        st.metric(t("components.currency.cash_non_home_pct"), f"{cash_nhp:.1f}%")
    with cash_m_cols[2]:
        c_icon = _RISK_COLORS.get(cash_risk, "⚪")
        c_label = _get_risk_label(cash_risk)
        st.metric(t("components.currency.risk_level"), f"{c_icon} {c_label}")

    _render_fx_donut(
        cash_bd, t("components.currency.cash_breakdown", currency=fx_home), fx_home
    )
    _render_fx_movements(fx_movements)
    _render_fx_rate_alerts(fx_data.get("fx_rate_alerts", []))

    # Cash-focused advice
    advice = fx_data.get("advice", [])
    cash_keyword = t("config.category.cash")
    cash_advice = [
        a for a in advice if cash_keyword in a or "💵" in a
    ]
    if cash_advice:
        st.markdown(t("components.currency.cash_advice_title"))
        _render_advice(cash_advice)

    # Telegram alert button
    if st.button(
        t("components.currency.telegram_button"),
        key="fx_alert_tg_cash_btn",
    ):
        level, msg = post_fx_exposure_alert()
        show_toast(level, msg)


def _render_total_tab(
    fx_data: dict, fx_home: str, fx_movements: list[dict]
) -> None:
    """Render the total asset currency exposure tab."""
    all_bd = fx_data.get("breakdown", [])
    all_nhp = fx_data.get("non_home_pct", 0.0)
    total_home = fx_data.get("total_value_home", 0.0)
    risk_level = fx_data.get("risk_level", "low")

    total_m_cols = st.columns(3)
    with total_m_cols[0]:
        st.metric(
            t("components.currency.total_value", currency=fx_home),
            _mask_money(total_home),
        )
    with total_m_cols[1]:
        st.metric(t("components.currency.non_home_pct"), f"{all_nhp:.1f}%")
    with total_m_cols[2]:
        t_icon = _RISK_COLORS.get(risk_level, "⚪")
        t_label = _get_risk_label(risk_level)
        st.metric(t("components.currency.risk_level"), f"{t_icon} {t_label}")

    _render_fx_donut(
        all_bd, t("components.currency.total_breakdown", currency=fx_home), fx_home
    )
    _render_fx_movements(fx_movements)
    _render_fx_rate_alerts(fx_data.get("fx_rate_alerts", []))

    # Full advice
    advice = fx_data.get("advice", [])
    if advice:
        st.markdown(t("components.currency.total_advice_title"))
        _render_advice(advice)


# ---------------------------------------------------------------------------
# Shared sub-renderers
# ---------------------------------------------------------------------------


def _render_fx_donut(
    bd_data: list[dict], title: str, home: str
) -> None:
    """Render a currency breakdown donut chart."""
    if not bd_data:
        st.info(t("components.currency.no_data"))
        return

    bd_labels = [b["currency"] for b in bd_data]
    bd_values = [b["value"] for b in bd_data]
    bd_text = [
        _mask_money(b["value"], "${:,.0f}") for b in bd_data
    ]
    bd_colors = [
        _CUR_COLORS.get(b["currency"], "#6B7280")
        for b in bd_data
    ]

    fig = go.Figure(
        go.Pie(
            labels=bd_labels,
            values=bd_values,
            hole=0.45,
            text=bd_text,
            textinfo=(
                "label+percent"
                if _is_privacy()
                else "label+text+percent"
            ),
            textposition="auto",
            marker=dict(colors=bd_colors),
            hovertemplate=(
                f"<b>%{{label}}</b><br>"
                f"{t('components.currency.chart.weight_pct')}：%{{percent}}<extra></extra>"
                if _is_privacy()
                else (
                    f"<b>%{{label}}</b><br>"
                    f"{t('components.currency.chart.market_value')}：%{{text}} {home}<br>"
                    f"{t('components.currency.chart.weight_pct')}：%{{percent}}<extra></extra>"
                )
            ),
        )
    )
    fig.update_layout(
        title=title,
        height=380,
        margin=dict(t=40, b=20, l=20, r=20),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_fx_movements(movements: list[dict]) -> None:
    """Render the FX movements table."""
    if not movements:
        return
    st.markdown(t("components.currency.movements_title"))
    mv_rows = []
    for mv in movements:
        direction_icon = (
            "📈"
            if mv["direction"] == "up"
            else ("📉" if mv["direction"] == "down" else "➡️")
        )
        mv_rows.append(
            {
                "": direction_icon,
                t("components.currency.movements.pair"): mv["pair"],
                t("components.currency.movements.current_rate"): (
                    PRIVACY_MASK
                    if _is_privacy()
                    else f"{mv['current_rate']:.4f}"
                ),
                t("components.currency.movements.change"): f"{mv['change_pct']:+.2f}%",
            }
        )
    st.dataframe(
        pd.DataFrame(mv_rows),
        use_container_width=True,
        hide_index=True,
    )


def _render_fx_rate_alerts(rate_alerts: list[dict]) -> None:
    """Render FX rate change alerts with colored badges."""
    if not rate_alerts:
        return
    st.markdown(t("components.currency.rate_alerts_title"))
    alert_rows = []
    for a in rate_alerts:
        badge, label_func = _ALERT_TYPE_BADGES.get(
            a["alert_type"], ("⚪", lambda: a["alert_type"])
        )
        direction_icon = (
            "📈" if a["direction"] == "up" else "📉"
        )
        alert_rows.append(
            {
                "": f"{badge} {direction_icon}",
                t("components.currency.alerts.type"): label_func(),
                t("components.currency.alerts.pair"): a["pair"],
                t("components.currency.alerts.period"): a["period_label"],
                t("components.currency.alerts.change"): f"{a['change_pct']:+.2f}%",
                t("components.currency.alerts.current_rate"): (
                    PRIVACY_MASK
                    if _is_privacy()
                    else f"{a['current_rate']:.4f}"
                ),
            }
        )
    st.dataframe(
        pd.DataFrame(alert_rows),
        use_container_width=True,
        hide_index=True,
    )


def _render_advice(advice_lines: list[str]) -> None:
    """Render advice lines, masking monetary amounts in privacy mode."""
    for adv in advice_lines:
        if _is_privacy():
            masked = _CURRENCY_AMOUNT_RE.sub(PRIVACY_MASK, adv)
            st.write(masked)
        else:
            st.write(adv)
