"""
Folio — Summary Dashboard Page (投資組合總覽).
At-a-glance view of market sentiment, portfolio KPIs, allocation, signals, and top holdings.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import (
    CATEGORY_COLOR_FALLBACK,
    CATEGORY_COLOR_MAP,
    CATEGORY_ICON_SHORT,
    DASHBOARD_ALLOCATION_CHART_HEIGHT,
    DASHBOARD_DRIFT_CHART_HEIGHT,
    DASHBOARD_TOP_HOLDINGS_LIMIT,
    DISPLAY_CURRENCY_OPTIONS,
    FEAR_GREED_GAUGE_BANDS,
    FEAR_GREED_GAUGE_HEIGHT,
    HEALTH_SCORE_GOOD_THRESHOLD,
    HEALTH_SCORE_WARN_THRESHOLD,
    HOLDING_ACTION_ICONS,
    PRIVACY_MASK,
    SCAN_SIGNAL_ICONS,
    get_cnn_unavailable_msg,
    get_fear_greed_label,
    get_holding_action_label,
    get_market_sentiment_label,
    get_category_labels,
    get_privacy_toggle_label,
)
from i18n import t
from utils import (
    fetch_fear_greed,
    fetch_great_minds,
    fetch_holdings,
    fetch_last_scan,
    fetch_profile,
    fetch_rebalance,
    fetch_stocks,
    format_utc_timestamp,
    invalidate_all_caches,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    on_privacy_change as _on_privacy_change,
    refresh_ui,
)


def _compute_health_score(stocks: list) -> tuple[float, int, int]:
    """Compute health score = % of active stocks with NORMAL signal.

    Returns (score_pct, normal_count, total_count).
    """
    if not stocks:
        return 0.0, 0, 0
    active = [s for s in stocks if s.get("is_active", True)]
    total = len(active)
    if total == 0:
        return 0.0, 0, 0
    normal_count = sum(1 for s in active if s.get("last_scan_signal", "NORMAL") == "NORMAL")
    return (normal_count / total) * 100, normal_count, total


def _health_color(score: float) -> str:
    """Return color keyword for the health score."""
    if score >= HEALTH_SCORE_GOOD_THRESHOLD:
        return "normal"
    if score >= HEALTH_SCORE_WARN_THRESHOLD:
        return "off"
    return "inverse"


# ---------------------------------------------------------------------------
# Page Layout
# ---------------------------------------------------------------------------

# -- Fetch data --
last_scan_data = fetch_last_scan()
stocks_data = fetch_stocks()
holdings_data = fetch_holdings()

# -- Title row: title | currency selector | privacy toggle | refresh --
_title_cols = st.columns([4, 1, 1, 1])
with _title_cols[0]:
    st.title(t("dashboard.title"))
with _title_cols[1]:
    display_currency = st.selectbox(
        t("dashboard.currency_selector"),
        options=DISPLAY_CURRENCY_OPTIONS,
        index=0,
        key="dashboard_currency",
        label_visibility="collapsed",
    )
with _title_cols[2]:
    st.toggle(get_privacy_toggle_label(), key="privacy_mode", on_change=_on_privacy_change)
with _title_cols[3]:
    if st.button(t("common.refresh"), use_container_width=True):
        invalidate_all_caches()
        refresh_ui()

rebalance_data = fetch_rebalance(display_currency)
profile_data = fetch_profile()


# ---------------------------------------------------------------------------
# Data Freshness Timestamps
# ---------------------------------------------------------------------------
_ts_parts: list[str] = []
browser_tz = st.session_state.get("browser_tz")

# Price data timestamp from rebalance
if rebalance_data and rebalance_data.get("calculated_at"):
    price_ts = format_utc_timestamp(rebalance_data["calculated_at"], browser_tz)
    _ts_parts.append(t("dashboard.price_updated", timestamp=price_ts))

# Last scan timestamp
if last_scan_data and last_scan_data.get("last_scanned_at"):
    scan_ts = format_utc_timestamp(last_scan_data["last_scanned_at"], browser_tz)
    _ts_parts.append(t("dashboard.last_scan", timestamp=scan_ts))

if _ts_parts:
    st.caption(" ｜ ".join(_ts_parts))
else:
    st.caption(t("dashboard.no_update_record"))


# ---------------------------------------------------------------------------
# Onboarding: first-time user with no data at all
# ---------------------------------------------------------------------------
# Page paths must match the strings in app.py st.Page(...) registration.
if not stocks_data and not rebalance_data:
    st.divider()
    st.info(t("dashboard.welcome"))
    _onb_a, _onb_b, _ = st.columns([1, 1, 2])
    with _onb_a:
        if st.button(t("dashboard.welcome_button_persona"), use_container_width=True):
            st.switch_page("views/allocation.py")
    with _onb_b:
        if st.button(t("dashboard.welcome_button_track"), use_container_width=True):
            st.switch_page("views/radar.py")
    st.stop()


# ---------------------------------------------------------------------------
# Zone B: Portfolio Pulse — 3-column hero section (above the fold)
# ---------------------------------------------------------------------------
fear_greed_data = fetch_fear_greed()

# Pre-compute values used inside the hero columns
_privacy = _is_privacy()
health_pct, normal_cnt, total_cnt = _compute_health_score(stocks_data or [])
market_status = (last_scan_data or {}).get("market_status")
sentiment_info = get_market_sentiment_label(market_status or "")
stock_count = len(stocks_data) if stocks_data else 0
holding_count = len(holdings_data) if holdings_data else 0

with st.container(border=True):
    _hero_left, _hero_mid, _hero_right = st.columns([2, 1, 1])

    # -- Left: Total Portfolio Value + Daily P&L --
    with _hero_left:
        if rebalance_data and rebalance_data.get("total_value") is not None:
            total_val = rebalance_data["total_value"]
            change_pct = rebalance_data.get("total_value_change_pct")
            change_amt = rebalance_data.get("total_value_change")

            if change_pct is not None and change_amt is not None:
                arrow = "▲" if change_pct >= 0 else "▼"
                if _privacy:
                    delta_str = f"{arrow}{abs(change_pct):.2f}%"
                else:
                    delta_str = f"{arrow}{abs(change_pct):.2f}% (${abs(change_amt):,.2f})"
            else:
                delta_str = None

            st.markdown(
                f'<p class="hero-label">{t("dashboard.total_market_value")}</p>'
                f'<p class="hero-value">{_mask_money(total_val)}</p>',
                unsafe_allow_html=True,
            )
            if delta_str:
                color_css = "#22c55e" if (change_pct or 0) >= 0 else "#ef4444"
                st.markdown(
                    f'<p class="hero-delta" style="color:{color_css}">{delta_str}</p>',
                    unsafe_allow_html=True,
                )
        else:
            st.metric(t("dashboard.total_market_value"), "N/A")

    # -- Center: Fear & Greed compact gauge --
    with _hero_mid:
        if fear_greed_data:
            fg_level = fear_greed_data.get("composite_level", "N/A")
            fg_score = fear_greed_data.get("composite_score", 50)
            fg_info = get_fear_greed_label(fg_level)
            vix_data = fear_greed_data.get("vix") or {}
            vix_val = vix_data.get("value")
            vix_change = vix_data.get("change_1d")
            cnn_data = fear_greed_data.get("cnn")
            cnn_score = cnn_data.get("score") if cnn_data else None

            gauge_title = fg_info["label"].split(" ", 1)[-1] if " " in fg_info["label"] else fg_info["label"]

            fig_gauge = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=fg_score,
                    title={"text": gauge_title, "font": {"size": 14}},
                    number={"suffix": "/100", "font": {"size": 22}},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1},
                        "bar": {"color": "#333333"},
                        "steps": [
                            {"range": band["range"], "color": band["color"]}
                            for band in FEAR_GREED_GAUGE_BANDS
                        ],
                    },
                )
            )
            fig_gauge.update_layout(
                height=FEAR_GREED_GAUGE_HEIGHT,
                margin=dict(l=10, r=10, t=30, b=5),
            )
            st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

            caption_parts: list[str] = []
            if vix_val is not None:
                vix_str = f"VIX={vix_val:.1f}"
                if vix_change is not None:
                    arrow = "▲" if vix_change > 0 else "▼"
                    vix_str += f" ({arrow}{abs(vix_change):.1f})"
                caption_parts.append(vix_str)
            if cnn_score is not None:
                caption_parts.append(f"CNN={cnn_score}")
            else:
                caption_parts.append(get_cnn_unavailable_msg())
            st.caption(" ｜ ".join(caption_parts))
        else:
            na_info = get_fear_greed_label("N/A")
            st.metric(t("dashboard.fear_greed_title"), na_info["label"])

    # -- Right: Market Sentiment + Health Score + Tracking/Holdings --
    with _hero_right:
        st.metric(t("dashboard.market_sentiment"), sentiment_info["label"])

        if total_cnt > 0:
            st.metric(
                t("dashboard.health_score"),
                f"{health_pct:.0f}%",
                delta=t("dashboard.health_delta", normal=normal_cnt, total=total_cnt),
                delta_color=_health_color(health_pct),
            )
        else:
            st.metric(t("dashboard.health_score"), "N/A")

        st.metric(
            t("dashboard.kpi.tracking_holdings"),
            t("dashboard.kpi.tracking_holdings_value", stocks=stock_count, holdings=holding_count),
        )


# ---------------------------------------------------------------------------
# Section 2: Signal Alerts (Action Required — before Allocation)
# ---------------------------------------------------------------------------
st.divider()
st.subheader(t("dashboard.signal_alerts_title"))

with st.container(border=True):
    if stocks_data:
        alert_stocks = [
            s for s in stocks_data
            if s.get("is_active", True) and s.get("last_scan_signal", "NORMAL") != "NORMAL"
        ]
        if alert_stocks:
            for s in alert_stocks:
                signal = s.get("last_scan_signal", "NORMAL")
                icon = SCAN_SIGNAL_ICONS.get(signal, "⚪")
                cat_label = get_category_labels().get(s.get("category", ""), s.get("category", ""))
                cat_short = cat_label.split("(")[0].strip()
                _a_icon, _a_ticker, _a_cat, _a_signal = st.columns([0.5, 2, 2, 2])
                with _a_icon:
                    st.markdown(icon)
                with _a_ticker:
                    st.markdown(f"**{s['ticker']}**")
                with _a_cat:
                    st.markdown(cat_short)
                with _a_signal:
                    st.markdown(f"`{signal}`")

            # Rebalance advice inline — only shown alongside actionable alerts
            advice = rebalance_data.get("advice", []) if rebalance_data else []
            if advice:
                st.caption(t("dashboard.rebalance_advice_title"))
                for item in advice[:5]:
                    st.caption(f"• {item}")
        else:
            st.success(t("dashboard.all_signals_normal"))
    else:
        st.info(t("dashboard.no_tracking_stocks"))
        _sig_a, _ = st.columns([1, 3])
        with _sig_a:
            if st.button(t("dashboard.button_goto_radar"), use_container_width=True):
                st.switch_page("views/radar.py")


# ---------------------------------------------------------------------------
# Section 3: Allocation at a Glance
# ---------------------------------------------------------------------------
st.divider()

if rebalance_data and profile_data and rebalance_data.get("categories"):
    breakdown = rebalance_data["categories"]
    st.subheader(t("dashboard.allocation_title"))

    target_alloc = profile_data.get("config", {})
    cat_labels = []
    target_vals = []
    actual_vals = []
    colors = []

    for cat_key, target_pct in target_alloc.items():
        cat_display = get_category_labels().get(cat_key, cat_key)
        icon = CATEGORY_ICON_SHORT.get(cat_key, "")
        cat_labels.append(f"{icon} {cat_display.split('(')[0].strip()}")
        target_vals.append(target_pct)
        cat_info = breakdown.get(cat_key, {})
        actual_vals.append(cat_info.get("current_pct", 0))
        colors.append(CATEGORY_COLOR_MAP.get(cat_key, CATEGORY_COLOR_FALLBACK))

    drift_labels = []
    drift_vals = []
    drift_colors = []
    for cat_key in target_alloc:
        cat_info = breakdown.get(cat_key, {})
        drift = cat_info.get("drift_pct", 0)
        icon = CATEGORY_ICON_SHORT.get(cat_key, "")
        drift_labels.append(f"{icon} {cat_key}")
        drift_vals.append(drift)
        drift_colors.append("red" if abs(drift) > 5 else "gray")

    with st.container(border=True):
        _alloc_col, _drift_col = st.columns([1, 1])

        with _alloc_col:
            # -- Dual Donut: Target vs Actual --
            fig_alloc = make_subplots(
                rows=1,
                cols=2,
                specs=[[{"type": "pie"}, {"type": "pie"}]],
                subplot_titles=[t("dashboard.chart.target"), t("dashboard.chart.actual")],
            )
            fig_alloc.add_trace(
                go.Pie(
                    labels=cat_labels,
                    values=target_vals,
                    hole=0.4,
                    marker=dict(colors=colors),
                    textinfo="percent",
                    hovertemplate=(
                        f"<b>%{{label}}</b><br>"
                        f"{t('dashboard.chart.target_pct')}：%{{percent}}<extra></extra>"
                    ),
                ),
                row=1,
                col=1,
            )
            fig_alloc.add_trace(
                go.Pie(
                    labels=cat_labels,
                    values=actual_vals,
                    hole=0.4,
                    marker=dict(colors=colors),
                    textinfo="percent",
                    hovertemplate=(
                        f"<b>%{{label}}</b><br>"
                        f"{t('dashboard.chart.actual_pct')}：%{{percent}}<extra></extra>"
                    ),
                ),
                row=1,
                col=2,
            )
            fig_alloc.update_layout(
                height=DASHBOARD_ALLOCATION_CHART_HEIGHT,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig_alloc, use_container_width=True, config={"displayModeBar": False})

        with _drift_col:
            # -- Drift Bar Chart --
            fig_drift = go.Figure(
                go.Bar(
                    x=drift_labels,
                    y=drift_vals,
                    marker_color=drift_colors,
                    text=[f"{d:+.1f}%" for d in drift_vals],
                    textposition="outside",
                )
            )
            fig_drift.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="+5%")
            fig_drift.add_hline(y=-5, line_dash="dash", line_color="orange", annotation_text="-5%")
            fig_drift.update_layout(
                title={"text": t("dashboard.drift_title"), "font": {"size": 14}, "x": 0.5, "xanchor": "center"},
                height=DASHBOARD_DRIFT_CHART_HEIGHT,
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis_title=t("dashboard.chart.drift_yaxis"),
                showlegend=False,
            )
            st.plotly_chart(fig_drift, use_container_width=True, config={"displayModeBar": False})
else:
    st.info(t("dashboard.no_allocation_data"))
    col_a, col_b, _ = st.columns([1, 1, 2])
    with col_a:
        if st.button(t("dashboard.button_setup_persona"), use_container_width=True):
            st.switch_page("views/allocation.py")
    with col_b:
        if st.button(t("dashboard.button_track_stock"), use_container_width=True):
            st.switch_page("views/radar.py")


# ---------------------------------------------------------------------------
# Section 4: Top Holdings
# ---------------------------------------------------------------------------
st.divider()
st.subheader(t("dashboard.top_holdings_title", limit=DASHBOARD_TOP_HOLDINGS_LIMIT))

if rebalance_data and rebalance_data.get("holdings_detail"):
    holdings_detail = rebalance_data["holdings_detail"]
    # Sort by weight descending
    sorted_holdings = sorted(holdings_detail, key=lambda h: h.get("weight_pct", 0), reverse=True)
    top_holdings = sorted_holdings[:DASHBOARD_TOP_HOLDINGS_LIMIT]

    privacy = _is_privacy()
    rows = []
    for h in top_holdings:
        cat = h.get("category", "")
        icon = CATEGORY_ICON_SHORT.get(cat, "")

        # Format daily change with arrow
        change_pct = h.get("change_pct")
        if change_pct is not None:
            arrow = "▲" if change_pct >= 0 else "▼"
            change_str = f"{arrow}{abs(change_pct):.2f}%"
        else:
            change_str = "N/A"

        rows.append({
            t("dashboard.holdings_table.ticker"): h.get("ticker", ""),
            t("dashboard.holdings_table.category"): f"{icon} {cat}",
            t("dashboard.holdings_table.weight"): f"{h.get('weight_pct', 0):.1f}%",
            t("dashboard.holdings_table.market_value"): PRIVACY_MASK if privacy else f"${h.get('market_value', 0):,.2f}",
            t("dashboard.holdings_table.daily_change"): change_str,
        })

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption(t("dashboard.no_holdings"))
else:
    st.info(t("dashboard.no_holdings_data"))
    _hold_a, _ = st.columns([1, 3])
    with _hold_a:
        if st.button(t("dashboard.button_add_holdings"), use_container_width=True):
            st.switch_page("views/allocation.py")


# ---------------------------------------------------------------------------
# Section 5: Smart Money Resonance Summary
# ---------------------------------------------------------------------------
st.divider()
st.subheader(t("dashboard.resonance.title"))

_great_minds = fetch_great_minds()

if _great_minds is None:
    st.caption(t("dashboard.resonance.unavailable"))
else:
    _gm_stocks = _great_minds.get("stocks", [])
    _gm_total = _great_minds.get("total_count", 0)

    if _gm_total == 0:
        st.info(t("dashboard.resonance.empty"))
        _sm_col, _ = st.columns([1, 3])
        with _sm_col:
            if st.button(t("dashboard.resonance.goto_smart_money"), use_container_width=True):
                st.switch_page("views/smart_money.py")
    else:
        # Top metrics row
        _gurus_with_overlap = len(
            {g["guru_id"] for s in _gm_stocks for g in s.get("gurus", [])}
        )
        _strongest = (
            f"{_gm_stocks[0]['ticker']} ×{_gm_stocks[0]['guru_count']}"
            if _gm_stocks else "—"
        )
        _mc1, _mc2, _mc3 = st.columns(3)
        _mc1.metric(t("dashboard.resonance.overlap_count"), _gm_total)
        _mc2.metric(t("dashboard.resonance.gurus_with_overlap"), _gurus_with_overlap)
        _mc3.metric(t("dashboard.resonance.strongest_signal"), _strongest)

        # Per-stock detail cards (top 5)
        for _stock in _gm_stocks[:5]:
            _ticker = _stock.get("ticker", "—")
            _gc = _stock.get("guru_count", 0)
            _gurus_list = _stock.get("gurus", [])
            _guru_lines = []
            for _g in _gurus_list:
                _name = _g.get("guru_display_name", "—")
                _action = _g.get("action", "UNCHANGED")
                _icon = HOLDING_ACTION_ICONS.get(_action, "⚪")
                _label = get_holding_action_label(_action)
                _weight = _g.get("weight_pct")
                _weight_str = (
                    f"  {_weight:.1f}%"
                    if _weight is not None and _action != "SOLD_OUT"
                    else ""
                )
                _guru_lines.append(f"  {_name}　{_icon} {_label}{_weight_str}")
            with st.container(border=True):
                _card_md = f"**{_ticker}**  ×{_gc}\n" + "\n".join(_guru_lines)
                st.markdown(_card_md)

        st.caption(t("dashboard.resonance.caption"))
        _sm_col2, _ = st.columns([1, 3])
        with _sm_col2:
            if st.button(t("dashboard.resonance.goto_smart_money"), use_container_width=True):
                st.switch_page("views/smart_money.py")
