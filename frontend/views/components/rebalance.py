"""
Folio — Rebalance Analysis Component (再平衡分析).
Reusable component for rendering Step 3: pie charts, drift, holdings detail, and X-Ray.
"""

from collections import defaultdict

import pandas as pd
import plotly.colors as pc
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import (
    ALLOCATION_CHART_HEIGHT,
    CATEGORY_COLOR_FALLBACK,
    CATEGORY_COLOR_MAP,
    CATEGORY_ICON_SHORT,
    DRIFT_CHART_HEIGHT,
    PRIVACY_MASK,
    XRAY_TOP_N_DISPLAY,
    XRAY_WARN_THRESHOLD_PCT,
    get_category_labels,
)
from i18n import t
from utils import (
    fetch_rebalance,
    format_utc_timestamp,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    mask_qty as _mask_qty,
    post_xray_alert,
    show_toast,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb_str(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'rgb(r, g, b)' for plotly.colors.n_colors."""
    h = hex_color.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_rebalance(
    profile: dict,
    holdings: list[dict],
    display_cur: str = "USD",
) -> None:
    """Render Step 3 — Rebalance Analysis.

    Renders pie charts, drift chart, holdings detail table, and X-Ray
    overlap analysis. The display currency selectbox and refresh button
    are owned by the orchestrator (allocation.py).

    Args:
        profile: Current user profile.
        holdings: Current holdings list.
        display_cur: Selected display currency (resolved by the orchestrator).
    """
    # Auto-fetch rebalance (cached TTL = CACHE_TTL_REBALANCE)
    rebalance = None
    with st.status(
        t("components.rebalance.loading"), expanded=True
    ) as _rb_status:
        rebalance = fetch_rebalance(display_currency=display_cur)
        if rebalance:
            _rb_status.update(
                label=t("components.rebalance.loaded"),
                state="complete",
                expanded=False,
            )
        else:
            _rb_status.update(
                label=t("components.rebalance.error"),
                state="error",
                expanded=True,
            )
            st.warning(t("components.rebalance.error_hint"))

    if not rebalance:
        return

    # Timestamp display
    calc_at = rebalance.get("calculated_at", "")
    if calc_at:
        browser_tz = st.session_state.get("browser_tz")
        st.caption(
            t("components.rebalance.data_time", time=format_utc_timestamp(calc_at, browser_tz))
        )

    st.metric(
        t("components.rebalance.total_value", currency=display_cur),
        _mask_money(rebalance["total_value"]),
    )

    _render_pie_charts(rebalance, display_cur)
    _render_drift_chart(rebalance)
    _render_advice(rebalance)
    _render_holdings_detail(rebalance, display_cur)
    _render_xray(rebalance, display_cur)


# ---------------------------------------------------------------------------
# Private renderers
# ---------------------------------------------------------------------------


def _render_pie_charts(rebalance: dict, display_cur: str) -> None:
    """Render target vs actual allocation dual pie chart."""
    cats_data = rebalance.get("categories", {})
    cat_names = list(cats_data.keys())
    cat_labels = [
        get_category_labels().get(c, c).split("(")[0].strip()
        for c in cat_names
    ]
    total_val = rebalance["total_value"]

    # --- Target Pie ---
    target_amounts = [
        round(total_val * cats_data[c]["target_pct"] / 100, 2)
        for c in cat_names
    ]
    target_text = [
        _mask_money(amt, "${:,.0f}") for amt in target_amounts
    ]

    # --- Actual Pie: per-stock breakdown ---
    detail = rebalance.get("holdings_detail", [])
    cat_groups: dict[str, list] = defaultdict(list)
    for d in detail:
        cat_groups[d["category"]].append(d)

    actual_labels = []
    actual_values = []
    actual_text = []
    actual_colors = []
    for cat, items in cat_groups.items():
        base = CATEGORY_COLOR_MAP.get(cat, CATEGORY_COLOR_FALLBACK)
        icon = CATEGORY_ICON_SHORT.get(cat, "")
        n = len(items)
        if n == 1:
            shades = [base]
        else:
            shades = pc.n_colors(
                _hex_to_rgb_str(base),
                "rgb(255, 255, 255)",
                n + 2,
                colortype="rgb",
            )[:-2]
        for i, d in enumerate(items):
            actual_labels.append(f"{icon} {d['ticker']}")
            actual_values.append(d["market_value"])
            actual_text.append(
                _mask_money(d["market_value"], "${:,.0f}")
            )
            actual_colors.append(shades[i])

    fig_pie = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=[
            t("components.rebalance.chart.target", currency=display_cur),
            t("components.rebalance.chart.actual", currency=display_cur),
        ],
    )

    # Target pie — categories with matching base colors
    target_colors = [
        CATEGORY_COLOR_MAP.get(c, CATEGORY_COLOR_FALLBACK)
        for c in cat_names
    ]
    _privacy = _is_privacy()
    fig_pie.add_trace(
        go.Pie(
            labels=cat_labels,
            values=target_amounts,
            hole=0.4,
            text=target_text,
            textinfo=(
                "label+percent"
                if _privacy
                else "label+text+percent"
            ),
            textposition="auto",
            marker=dict(colors=target_colors),
            hovertemplate=(
                f"<b>%{{label}}</b><br>"
                f"{t('components.rebalance.chart.weight_pct')}：%{{percent}}<extra></extra>"
                if _privacy
                else (
                    f"<b>%{{label}}</b><br>"
                    f"{t('components.rebalance.chart.target_amount')}：%{{text}} {display_cur}<br>"
                    f"{t('components.rebalance.chart.weight_pct')}：%{{percent}}<extra></extra>"
                )
            ),
        ),
        row=1,
        col=1,
    )

    # Actual pie — individual stocks with category-colored shades
    fig_pie.add_trace(
        go.Pie(
            labels=actual_labels,
            values=actual_values,
            hole=0.4,
            text=actual_text,
            textinfo=(
                "label+percent"
                if _privacy
                else "label+text+percent"
            ),
            textposition="auto",
            marker=dict(colors=actual_colors),
            hovertemplate=(
                f"<b>%{{label}}</b><br>"
                f"{t('components.rebalance.chart.weight_pct')}：%{{percent}}<extra></extra>"
                if _privacy
                else (
                    f"<b>%{{label}}</b><br>"
                    f"{t('components.rebalance.chart.market_value')}：%{{text}} {display_cur}<br>"
                    f"{t('components.rebalance.chart.weight_pct')}：%{{percent}}<extra></extra>"
                )
            ),
        ),
        row=1,
        col=2,
    )

    fig_pie.update_layout(
        height=ALLOCATION_CHART_HEIGHT,
        margin=dict(t=40, b=20, l=20, r=20),
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)


def _render_drift_chart(rebalance: dict) -> None:
    """Render the category drift bar chart."""
    cats_data = rebalance.get("categories", {})
    cat_names = list(cats_data.keys())
    cat_labels = [
        get_category_labels().get(c, c).split("(")[0].strip()
        for c in cat_names
    ]
    drift_vals = [cats_data[c]["drift_pct"] for c in cat_names]
    colors = [
        "#ef4444" if d > 0 else "#22c55e" for d in drift_vals
    ]
    fig_drift = go.Figure(
        go.Bar(
            x=cat_labels,
            y=drift_vals,
            marker_color=colors,
            text=[f"{d:+.1f}%" for d in drift_vals],
            textposition="outside",
        )
    )
    fig_drift.update_layout(
        title=t("components.rebalance.drift_title"),
        yaxis_title=t("components.rebalance.drift_yaxis"),
        height=DRIFT_CHART_HEIGHT,
        margin=dict(t=40, b=20, l=40, r=20),
    )
    st.plotly_chart(fig_drift, use_container_width=True)


def _render_advice(rebalance: dict) -> None:
    """Render rebalance advice lines."""
    st.markdown(t("components.rebalance.advice_title"))
    for adv in rebalance.get("advice", []):
        st.write(adv)


def _render_holdings_detail(
    rebalance: dict, display_cur: str
) -> None:
    """Render the per-holding detail table."""
    detail = rebalance.get("holdings_detail", [])
    if not detail:
        return

    st.divider()
    st.markdown(t("components.rebalance.holdings_title", currency=display_cur))
    detail_rows = []
    for d in detail:
        cat_lbl = (
            get_category_labels().get(d["category"], d["category"])
            .split("(")[0]
            .strip()
        )

        # 計算未實現損益
        cur_price = d.get("current_price")
        avg_cost = d.get("avg_cost")
        qty = d.get("quantity", 0)
        fx = d.get("fx", 1.0)

        pl_value = None
        pl_pct = None
        if (
            cur_price is not None
            and avg_cost is not None
            and avg_cost > 0
        ):
            pl_value = (cur_price - avg_cost) * qty * fx
            pl_pct = ((cur_price - avg_cost) / avg_cost) * 100

        # 格式化 P/L 顯示
        if _is_privacy():
            pl_display = PRIVACY_MASK
            pl_pct_display = PRIVACY_MASK
        elif pl_value is not None:
            sign = "+" if pl_value >= 0 else ""
            pl_display = f"{sign}${pl_value:,.2f}"
            pl_pct_display = f"{sign}{pl_pct:.2f}%"
        else:
            pl_display = "—"
            pl_pct_display = "—"

        detail_rows.append(
            {
                t("components.rebalance.table.ticker"): d["ticker"],
                t("components.rebalance.table.category"): cat_lbl,
                t("components.rebalance.table.currency"): d.get("currency", "USD"),
                t("components.rebalance.table.quantity"): _mask_qty(d["quantity"]),
                t("components.rebalance.table.current_price"): (
                    _mask_money(d["current_price"])
                    if d.get("current_price")
                    else "—"
                ),
                t("components.rebalance.table.avg_cost"): (
                    _mask_money(d["avg_cost"])
                    if d.get("avg_cost")
                    else "—"
                ),
                t("components.rebalance.table.market_value", currency=display_cur): _mask_money(
                    d["market_value"]
                ),
                t("components.rebalance.table.unrealized_pl"): pl_display,
                t("components.rebalance.table.pl_pct"): pl_pct_display,
                t("components.rebalance.table.weight"): f"{d['weight_pct']:.1f}%",
            }
        )

    detail_df = pd.DataFrame(detail_rows)
    st.dataframe(
        detail_df,
        use_container_width=True,
        hide_index=True,
    )


def _render_xray(rebalance: dict, display_cur: str) -> None:
    """Render the X-Ray portfolio overlap analysis."""
    xray = rebalance.get("xray", [])
    if not xray:
        return

    st.divider()
    st.markdown(
        t("components.rebalance.xray_title", currency=display_cur)
    )
    st.caption(t("components.rebalance.xray_caption"))

    # -- Warning callouts --
    for entry in xray:
        if (
            entry["total_weight_pct"] > XRAY_WARN_THRESHOLD_PCT
            and entry["indirect_value"] > 0
        ):
            sources = ", ".join(
                entry.get("indirect_sources", [])
            )
            st.warning(
                t("components.rebalance.xray_warning",
                  symbol=entry['symbol'],
                  direct_pct=entry['direct_weight_pct'],
                  sources=sources,
                  total_pct=entry['total_weight_pct'],
                  threshold=XRAY_WARN_THRESHOLD_PCT)
            )

    # -- Stacked bar chart (top N) --
    top_xray = xray[:XRAY_TOP_N_DISPLAY]
    xray_symbols = [e["symbol"] for e in reversed(top_xray)]
    xray_direct = [
        e["direct_weight_pct"] for e in reversed(top_xray)
    ]
    xray_indirect = [
        e["indirect_weight_pct"] for e in reversed(top_xray)
    ]

    fig_xray = go.Figure()
    fig_xray.add_trace(
        go.Bar(
            y=xray_symbols,
            x=xray_direct,
            name=t("components.rebalance.xray.direct"),
            orientation="h",
            marker_color="#4A90D9",
            text=[
                f"{v:.1f}%" if v > 0.5 else ""
                for v in xray_direct
            ],
            textposition="inside",
        )
    )
    fig_xray.add_trace(
        go.Bar(
            y=xray_symbols,
            x=xray_indirect,
            name=t("components.rebalance.xray.indirect"),
            orientation="h",
            marker_color="#F5A623",
            text=[
                f"{v:.1f}%" if v > 0.5 else ""
                for v in xray_indirect
            ],
            textposition="inside",
        )
    )
    # Threshold line
    fig_xray.add_vline(
        x=XRAY_WARN_THRESHOLD_PCT,
        line_dash="dash",
        line_color="red",
        annotation_text=t("components.rebalance.xray.threshold", threshold=XRAY_WARN_THRESHOLD_PCT),
        annotation_position="top right",
    )
    fig_xray.update_layout(
        barmode="stack",
        height=max(300, len(top_xray) * 28 + 80),
        margin=dict(t=30, b=20, l=80, r=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis_title=t("components.rebalance.xray.xaxis"),
    )
    st.plotly_chart(fig_xray, use_container_width=True)

    # -- Summary table --
    xray_rows = []
    for e in xray:
        xray_rows.append(
            {
                t("components.rebalance.xray.table.symbol"): e["symbol"],
                t("components.rebalance.xray.table.name"): e.get("name", ""),
                t("components.rebalance.xray.table.direct_pct"): f"{e['direct_weight_pct']:.1f}",
                t("components.rebalance.xray.table.indirect_pct"): f"{e['indirect_weight_pct']:.1f}",
                t("components.rebalance.xray.table.total_pct"): f"{e['total_weight_pct']:.1f}",
                t("components.rebalance.xray.table.direct_value", currency=display_cur): _mask_money(
                    e["direct_value"], "${:,.0f}"
                ),
                t("components.rebalance.xray.table.indirect_value", currency=display_cur): _mask_money(
                    e["indirect_value"], "${:,.0f}"
                ),
                t("components.rebalance.xray.table.sources"): ", ".join(
                    e.get("indirect_sources", [])
                ),
            }
        )
    xray_df = pd.DataFrame(xray_rows)
    st.dataframe(
        xray_df,
        use_container_width=True,
        hide_index=True,
    )

    # -- Telegram alert button --
    if st.button(
        t("components.rebalance.xray_telegram_button"),
        key="xray_tg_btn",
    ):
        level, msg = post_xray_alert(display_cur)
        show_toast(level, msg)
