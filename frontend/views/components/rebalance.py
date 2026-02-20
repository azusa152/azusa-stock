"""
Folio — Rebalance Analysis Component (再平衡分析).
Reusable component for rendering Step 3: pie charts, drift, holdings detail, and X-Ray.
"""

from collections import defaultdict

import pandas as pd
import plotly.colors as pc
import plotly.express as px
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
# Drift chart reference bands (P6 — tolerance zone visualisation)
# ---------------------------------------------------------------------------
_DRIFT_WARN_PCT = 5.0   # yellow caution band
_DRIFT_ALERT_PCT = 10.0  # orange alert band


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_to_rgb_str(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'rgb(r, g, b)' for plotly.colors.n_colors."""
    h = hex_color.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


def _calc_pl_pct(holding: dict) -> float:
    """Return unrealized P/L % from a holdings_detail entry, or 0.0 if data is missing."""
    cur_price = holding.get("current_price")
    avg_cost = holding.get("avg_cost")
    if cur_price is not None and avg_cost is not None and avg_cost > 0:
        return ((cur_price - avg_cost) / avg_cost) * 100
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_rebalance(
    profile: dict,
    holdings: list[dict],
    display_cur: str = "USD",
) -> None:
    """Render Rebalance Analysis tab.

    Renders health score, pie/treemap charts, drift chart with dollar amounts,
    holdings detail table, X-Ray overlap analysis, and sector heatmap.

    Args:
        profile: Current user profile.
        holdings: Current holdings list.
        display_cur: Selected display currency (resolved by the orchestrator).
    """
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

    # Timestamp
    calc_at = rebalance.get("calculated_at", "")
    if calc_at:
        browser_tz = st.session_state.get("browser_tz")
        st.caption(
            t("components.rebalance.data_time", time=format_utc_timestamp(calc_at, browser_tz))
        )

    # P0 — Health Score Banner
    _render_health_score_banner(rebalance)

    st.metric(
        t("components.rebalance.total_value", currency=display_cur),
        _mask_money(rebalance["total_value"]),
    )

    # P1 — Chart type toggle (Pies vs Treemap)
    view_type = st.radio(
        t("components.rebalance.view_toggle"),
        [
            t("components.rebalance.view_pies"),
            t("components.rebalance.view_treemap"),
        ],
        horizontal=True,
        key="rebalance_chart_view",
        label_visibility="collapsed",
    )

    if view_type == t("components.rebalance.view_pies"):
        _render_pie_charts(rebalance, display_cur)
    else:
        _render_treemap(rebalance, display_cur)

    # P2 — Drift chart with dollar amounts + P6 reference bands
    _render_drift_chart(rebalance, display_cur)

    _render_advice(rebalance)

    # P3 — Holdings table with daily change and weight progress bar
    _render_holdings_detail(rebalance, display_cur)

    # X-Ray
    _render_xray(rebalance, display_cur)

    # P5 — Sector heatmap
    _render_sector_heatmap(rebalance, display_cur)


# ---------------------------------------------------------------------------
# Private renderers
# ---------------------------------------------------------------------------


def _render_health_score_banner(rebalance: dict) -> None:
    """Render P0 — Portfolio Health Score banner."""
    health_score = rebalance.get("health_score", 100)
    health_level = rebalance.get("health_level", "healthy")

    color_map = {
        "healthy": "#22c55e",
        "caution": "#eab308",
        "alert": "#ef4444",
    }
    icon_map = {
        "healthy": "✅",
        "caution": "⚠️",
        "alert": "🚨",
    }

    color = color_map.get(health_level, "#9CA3AF")
    icon = icon_map.get(health_level, "⚪")
    level_label = t(f"components.rebalance.health.{health_level}")
    score_suffix = t("components.rebalance.health.score_suffix")
    banner_label = t("components.rebalance.health.label")

    st.markdown(
        f"""
        <div style="
            padding: 12px 16px;
            border-radius: 8px;
            background: {color}1A;
            border-left: 4px solid {color};
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        ">
            <span style="font-size: 1.6em; margin-right: 14px; line-height: 1;">{icon}</span>
            <div>
                <div style="font-size: 0.8em; opacity: 0.6; text-transform: uppercase;
                            letter-spacing: 0.05em; margin-bottom: 2px;">
                    {banner_label}
                </div>
                <div style="font-size: 1.25em; font-weight: 700; color: {color};">
                    {health_score} {score_suffix} — {level_label}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_pie_charts(rebalance: dict, display_cur: str) -> None:
    """Render target vs actual allocation dual pie chart."""
    cats_data = rebalance.get("categories", {})
    cat_names = list(cats_data.keys())
    cat_labels = [
        get_category_labels().get(c, c).split("(")[0].strip()
        for c in cat_names
    ]
    total_val = rebalance["total_value"]

    # Target Pie
    target_amounts = [
        round(total_val * cats_data[c]["target_pct"] / 100, 2)
        for c in cat_names
    ]
    target_text = [_mask_money(amt, "${:,.0f}") for amt in target_amounts]

    # Actual Pie: per-stock breakdown
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
            actual_text.append(_mask_money(d["market_value"], "${:,.0f}"))
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

    target_colors = [
        CATEGORY_COLOR_MAP.get(c, CATEGORY_COLOR_FALLBACK) for c in cat_names
    ]
    _privacy = _is_privacy()
    fig_pie.add_trace(
        go.Pie(
            labels=cat_labels,
            values=target_amounts,
            hole=0.4,
            text=target_text,
            textinfo="label+percent" if _privacy else "label+text+percent",
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

    fig_pie.add_trace(
        go.Pie(
            labels=actual_labels,
            values=actual_values,
            hole=0.4,
            text=actual_text,
            textinfo="label+percent" if _privacy else "label+text+percent",
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


def _render_treemap(rebalance: dict, display_cur: str) -> None:
    """Render P1 — Treemap view: Category > Ticker, sized by market value, colored by P/L %."""
    detail = rebalance.get("holdings_detail", [])
    if not detail:
        return

    st.caption(t("components.rebalance.treemap_title"))

    lbl_weight = t("components.rebalance.treemap_weight")
    lbl_pl = t("components.rebalance.treemap_pl")
    lbl_colorbar = t("components.rebalance.treemap_colorbar")

    rows = []
    for d in detail:
        cat_lbl = (
            get_category_labels().get(d["category"], d["category"])
            .split("(")[0]
            .strip()
        )
        icon = CATEGORY_ICON_SHORT.get(d["category"], "")

        rows.append(
            {
                "category": f"{icon} {cat_lbl}",
                "ticker": d["ticker"],
                "market_value": d["market_value"],
                "pl_pct": _calc_pl_pct(d),
                "weight_pct": d["weight_pct"],
            }
        )

    df = pd.DataFrame(rows)

    fig = px.treemap(
        df,
        path=["category", "ticker"],
        values="market_value",
        color="pl_pct",
        color_continuous_scale=["#ef4444", "#d1d5db", "#22c55e"],
        color_continuous_midpoint=0,
        custom_data=["weight_pct", "pl_pct"],
    )
    fig.update_traces(
        textinfo="label+percent root",
        hovertemplate=(
            "<b>%{label}</b><br>"
            + (f"{lbl_weight}: %{{customdata[0]:.1f}}%<extra></extra>" if _is_privacy() else
               f"{display_cur} %{{value:,.0f}}<br>"
               f"{lbl_weight}: %{{customdata[0]:.1f}}%<br>"
               f"{lbl_pl}: %{{customdata[1]:+.1f}}%<extra></extra>")
        ),
    )
    fig.update_layout(
        height=ALLOCATION_CHART_HEIGHT,
        margin=dict(t=10, b=0, l=0, r=0),
        coloraxis_colorbar=dict(
            title=lbl_colorbar,
            tickformat="+.0f",
            thickness=12,
            len=0.7,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_drift_chart(rebalance: dict, display_cur: str = "USD") -> None:
    """Render P2 + P6 — Drift bar chart with dollar amounts and tolerance bands."""
    cats_data = rebalance.get("categories", {})
    cat_names = list(cats_data.keys())
    cat_labels = [
        get_category_labels().get(c, c).split("(")[0].strip()
        for c in cat_names
    ]
    total_val = rebalance["total_value"]
    drift_vals = [cats_data[c]["drift_pct"] for c in cat_names]
    colors = ["#ef4444" if d > 0 else "#22c55e" for d in drift_vals]

    # P2 — annotate each bar with % and dollar amount needed to rebalance
    _privacy = _is_privacy()
    text_labels = []
    for d in drift_vals:
        if _privacy or total_val <= 0:
            text_labels.append(f"{d:+.1f}%")
        else:
            amount = abs(total_val * d / 100)
            action = (
                t("components.rebalance.drift_action_sell")
                if d > 0
                else t("components.rebalance.drift_action_buy")
            )
            text_labels.append(
                f"{d:+.1f}%  {action} {display_cur} {amount:,.0f}"
            )

    fig_drift = go.Figure(
        go.Bar(
            x=cat_labels,
            y=drift_vals,
            marker_color=colors,
            text=text_labels,
            textposition="outside",
            textfont_size=11,
            cliponaxis=False,
        )
    )

    # P6 — tolerance band reference lines
    fig_drift.add_hline(
        y=_DRIFT_WARN_PCT,
        line_dash="dot",
        line_color="#f59e0b",
        line_width=1,
        annotation_text=f"+{_DRIFT_WARN_PCT:.0f}%",
        annotation_position="right",
        annotation_font_color="#f59e0b",
    )
    fig_drift.add_hline(
        y=-_DRIFT_WARN_PCT,
        line_dash="dot",
        line_color="#f59e0b",
        line_width=1,
        annotation_text=f"-{_DRIFT_WARN_PCT:.0f}%",
        annotation_position="right",
        annotation_font_color="#f59e0b",
    )
    fig_drift.add_hline(
        y=_DRIFT_ALERT_PCT,
        line_dash="dash",
        line_color="#f97316",
        line_width=1,
        annotation_text=f"+{_DRIFT_ALERT_PCT:.0f}%",
        annotation_position="right",
        annotation_font_color="#f97316",
    )
    fig_drift.add_hline(
        y=-_DRIFT_ALERT_PCT,
        line_dash="dash",
        line_color="#f97316",
        line_width=1,
        annotation_text=f"-{_DRIFT_ALERT_PCT:.0f}%",
        annotation_position="right",
        annotation_font_color="#f97316",
    )

    fig_drift.update_layout(
        title=t("components.rebalance.drift_title"),
        yaxis_title=t("components.rebalance.drift_yaxis"),
        height=DRIFT_CHART_HEIGHT,
        margin=dict(t=40, b=20, l=40, r=60),
        uniformtext_minsize=8,
        uniformtext_mode="hide",
    )
    st.plotly_chart(fig_drift, use_container_width=True)


def _render_advice(rebalance: dict) -> None:
    """Render rebalance advice lines."""
    st.markdown(t("components.rebalance.advice_title"))
    for adv in rebalance.get("advice", []):
        st.write(adv)


def _render_holdings_detail(rebalance: dict, display_cur: str) -> None:
    """Render P3 — Holdings detail table with daily change column and weight progress bar."""
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

        cur_price = d.get("current_price")
        avg_cost = d.get("avg_cost")
        qty = d.get("quantity", 0)
        fx = d.get("fx", 1.0)
        change_pct = d.get("change_pct")

        pl_pct = _calc_pl_pct(d)
        pl_value = None
        if cur_price is not None and avg_cost is not None and avg_cost > 0:
            pl_value = (cur_price - avg_cost) * qty * fx

        # Formatted strings
        if _is_privacy():
            pl_display = PRIVACY_MASK
            pl_pct_display = PRIVACY_MASK
            change_display = PRIVACY_MASK
        else:
            if pl_value is not None:
                sign = "+" if pl_value >= 0 else ""
                pl_display = f"{sign}${pl_value:,.2f}"
                pl_pct_display = f"{sign}{pl_pct:.2f}%"
            else:
                pl_display = "—"
                pl_pct_display = "—"

            if change_pct is not None:
                change_sign = "+" if change_pct >= 0 else ""
                change_display = f"{change_sign}{change_pct:.2f}%"
            else:
                change_display = "N/A"

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
                    _mask_money(d["avg_cost"]) if d.get("avg_cost") else "—"
                ),
                t("components.rebalance.table.market_value", currency=display_cur): _mask_money(
                    d["market_value"]
                ),
                t("components.rebalance.table.unrealized_pl"): pl_display,
                t("components.rebalance.table.pl_pct"): pl_pct_display,
                t("components.rebalance.table.daily_change"): change_display,
                # Numeric weight for ProgressColumn
                "_weight_num": d["weight_pct"],
            }
        )

    detail_df = pd.DataFrame(detail_rows)
    weight_col = t("components.rebalance.table.weight")
    detail_df[weight_col] = detail_df["_weight_num"]
    detail_df = detail_df.drop(columns=["_weight_num"])

    st.dataframe(
        detail_df,
        column_config={
            weight_col: st.column_config.ProgressColumn(
                weight_col,
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
        use_container_width=True,
        hide_index=True,
    )


def _render_xray(rebalance: dict, display_cur: str) -> None:
    """Render the X-Ray portfolio overlap analysis."""
    xray = rebalance.get("xray", [])
    if not xray:
        return

    st.divider()
    st.markdown(t("components.rebalance.xray_title", currency=display_cur))
    st.caption(t("components.rebalance.xray_caption"))

    for entry in xray:
        if (
            entry["total_weight_pct"] > XRAY_WARN_THRESHOLD_PCT
            and entry["indirect_value"] > 0
        ):
            sources = ", ".join(entry.get("indirect_sources", []))
            st.warning(
                t(
                    "components.rebalance.xray_warning",
                    symbol=entry["symbol"],
                    direct_pct=entry["direct_weight_pct"],
                    sources=sources,
                    total_pct=entry["total_weight_pct"],
                    threshold=XRAY_WARN_THRESHOLD_PCT,
                )
            )

    top_xray = xray[:XRAY_TOP_N_DISPLAY]
    xray_symbols = [e["symbol"] for e in reversed(top_xray)]
    xray_direct = [e["direct_weight_pct"] for e in reversed(top_xray)]
    xray_indirect = [e["indirect_weight_pct"] for e in reversed(top_xray)]

    fig_xray = go.Figure()
    fig_xray.add_trace(
        go.Bar(
            y=xray_symbols,
            x=xray_direct,
            name=t("components.rebalance.xray.direct"),
            orientation="h",
            marker_color="#4A90D9",
            text=[f"{v:.1f}%" if v > 0.5 else "" for v in xray_direct],
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
            text=[f"{v:.1f}%" if v > 0.5 else "" for v in xray_indirect],
            textposition="inside",
        )
    )
    fig_xray.add_vline(
        x=XRAY_WARN_THRESHOLD_PCT,
        line_dash="dash",
        line_color="red",
        annotation_text=t(
            "components.rebalance.xray.threshold", threshold=XRAY_WARN_THRESHOLD_PCT
        ),
        annotation_position="top right",
    )
    fig_xray.update_layout(
        barmode="stack",
        height=max(300, len(top_xray) * 28 + 80),
        margin=dict(t=30, b=20, l=80, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title=t("components.rebalance.xray.xaxis"),
    )
    st.plotly_chart(fig_xray, use_container_width=True)

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
    st.dataframe(xray_df, use_container_width=True, hide_index=True)

    if st.button(t("components.rebalance.xray_telegram_button"), key="xray_tg_btn"):
        level, msg = post_xray_alert(display_cur)
        show_toast(level, msg)


def _render_sector_heatmap(rebalance: dict, display_cur: str) -> None:
    """Render P5 — Sector concentration heatmap for equity holdings."""
    sector_exp = rebalance.get("sector_exposure", [])
    if not sector_exp:
        st.divider()
        st.caption(t("components.rebalance.sector_no_data"))
        return

    st.divider()
    st.markdown(t("components.rebalance.sector_title"))

    sectors = [e["sector"] for e in sector_exp]
    weights = [e["weight_pct"] for e in sector_exp]
    equity_pcts = [e["equity_pct"] for e in sector_exp]

    # Color-code bars by weight magnitude
    max_weight = max(weights) if weights else 1.0
    bar_colors = [
        "#ef4444" if w / max_weight > 0.6 else
        "#f59e0b" if w / max_weight > 0.35 else
        "#3b82f6"
        for w in weights
    ]

    fig = go.Figure(
        go.Bar(
            x=weights,
            y=sectors,
            orientation="h",
            marker_color=bar_colors,
            text=[
                f"{w:.1f}%" if _is_privacy() else f"{w:.1f}% ({e:.1f}% of equity)"
                for w, e in zip(weights, equity_pcts)
            ],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                + (
                    "%{x:.1f}% of portfolio<extra></extra>"
                    if _is_privacy()
                    else "%{x:.1f}% of portfolio<br>%{customdata:.1f}% of equity<extra></extra>"
                )
            ),
            customdata=equity_pcts,
        )
    )
    fig.update_layout(
        title=t("components.rebalance.sector_chart_title"),
        height=max(280, len(sectors) * 32 + 80),
        xaxis_title=t("components.rebalance.sector_xaxis"),
        margin=dict(t=40, b=20, l=10, r=80),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)
