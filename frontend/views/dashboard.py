"""
Folio — Summary Dashboard Page (投資組合總覽).
At-a-glance view of market sentiment, portfolio KPIs, allocation, signals, and top holdings.
"""

from datetime import date, datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import (
    BUY_OPPORTUNITY_SIGNALS,
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
    PERFORMANCE_CHART_HEIGHT,
    PERFORMANCE_PERIOD_OPTIONS,
    PRIVACY_MASK,
    RISK_WARNING_SIGNALS,
    SCAN_SIGNAL_ICONS,
    SPARKLINE_HEIGHT,
    get_cnn_unavailable_msg,
    get_fear_greed_label,
    get_holding_action_label,
    get_market_sentiment_label,
    get_category_labels,
    get_privacy_toggle_label,
)
from i18n import t
from utils import (
    fetch_enriched_stocks,
    fetch_fear_greed,
    fetch_great_minds,
    fetch_holdings,
    fetch_last_scan,
    fetch_profile,
    fetch_rebalance,
    fetch_snapshots,
    fetch_stocks,
    fetch_twr,
    format_utc_timestamp,
    invalidate_all_caches,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    on_privacy_change as _on_privacy_change,
    refresh_ui,
)


def _compute_health_score(
    stocks: list, enriched_signal_map: dict[str, str] | None = None
) -> tuple[float, int, int]:
    """Compute health score = % of active stocks with NORMAL signal.

    Uses real-time computed_signal from enriched data when available (same
    source as the radar page), falling back to persisted last_scan_signal.

    Returns (score_pct, normal_count, total_count).
    """
    if not stocks:
        return 0.0, 0, 0
    active = [s for s in stocks if s.get("is_active", True)]
    total = len(active)
    if total == 0:
        return 0.0, 0, 0

    def _effective_signal(s: dict) -> str:
        fallback = s.get("last_scan_signal", "NORMAL")
        if enriched_signal_map:
            return enriched_signal_map.get(s.get("ticker", ""), fallback)
        return fallback

    normal_count = sum(1 for s in active if _effective_signal(s) == "NORMAL")
    return (normal_count / total) * 100, normal_count, total


def _health_color(score: float) -> str:
    """Return color keyword for the health score."""
    if score >= HEALTH_SCORE_GOOD_THRESHOLD:
        return "normal"
    if score >= HEALTH_SCORE_WARN_THRESHOLD:
        return "off"
    return "inverse"


@st.fragment
def _render_performance_chart(snapshots: list[dict]) -> None:
    """Render the portfolio performance line chart with period selector.

    Both the portfolio and S&P 500 benchmark are normalised to % return from
    the start of the selected period so they share a meaningful Y-axis.
    """
    from datetime import timedelta

    period_keys = list(PERFORMANCE_PERIOD_OPTIONS.keys())
    period_labels = [t(f"dashboard.performance_period_{k.lower()}") for k in period_keys]
    default_idx = period_keys.index("1M")

    selected_label = st.radio(
        t("dashboard.performance_title"),
        period_labels,
        index=default_idx,
        horizontal=True,
        key="perf_period",
        label_visibility="collapsed",
    )
    selected_key = period_keys[period_labels.index(selected_label)]
    requested_days = PERFORMANCE_PERIOD_OPTIONS[selected_key]

    # Filter client-side using date cutoffs so gaps (weekends/holidays) don't
    # cause a slice-index to reach further back than intended.
    if selected_key == "YTD":
        cutoff = date(date.today().year, 1, 1).isoformat()
    elif requested_days == 0:
        cutoff = ""  # ALL: no cutoff
    else:
        cutoff = (date.today() - timedelta(days=requested_days)).isoformat()

    filtered = [s for s in snapshots if s["snapshot_date"] >= cutoff] if cutoff else snapshots

    if not filtered:
        st.caption(t("dashboard.performance_no_data"))
        return

    dates = [s["snapshot_date"] for s in filtered]
    values = [s["total_value"] for s in filtered]
    benchmarks = [s.get("benchmark_value") for s in filtered]

    # Normalise to % return from the first point in the period
    base_val = values[0] or 1
    pct_returns = [(v / base_val - 1) * 100 for v in values]

    is_up = pct_returns[-1] >= 0
    line_color = "#00C805" if is_up else "#FF5252"
    fill_color = "rgba(0,200,5,0.07)" if is_up else "rgba(255,82,82,0.07)"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=pct_returns,
            mode="lines",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            customdata=values,
            hovertemplate="%{x}<br>%{y:+.2f}%  ($%{customdata:,.0f})<extra></extra>",
            name=t("dashboard.total_market_value"),
        )
    )

    # Benchmark: normalise S&P 500 to the same period start for a fair % comparison
    bench_clean = [(d, b) for d, b in zip(dates, benchmarks) if b is not None]
    if bench_clean:
        b_dates, b_vals = zip(*bench_clean)
        base_b = b_vals[0] or 1
        b_pct = [(b / base_b - 1) * 100 for b in b_vals]
        fig.add_trace(
            go.Scatter(
                x=list(b_dates),
                y=b_pct,
                mode="lines",
                line=dict(color="#888", width=1, dash="dot"),
                name=t("dashboard.performance_benchmark_label"),
                hovertemplate="%{x}<br>S&P500 %{y:+.2f}%<extra></extra>",
            )
        )

    fig.update_layout(
        height=PERFORMANCE_CHART_HEIGHT,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(128,128,128,0.15)",
            ticksuffix="%",
            zeroline=True,
            zerolinecolor="rgba(128,128,128,0.3)",
        ),
        xaxis=dict(showgrid=False),
        showlegend=bool(bench_clean),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_sparkline(snapshots: list[dict]) -> None:
    """Render a mini 30-day sparkline zoomed into the variation range."""
    from datetime import timedelta

    cutoff = (date.today() - timedelta(days=30)).isoformat()
    recent = [s for s in snapshots if s["snapshot_date"] >= cutoff]
    if len(recent) < 2:
        return
    dates = [s["snapshot_date"] for s in recent]
    values = [s["total_value"] for s in recent]
    is_up = values[-1] >= values[0]
    color = "#00C805" if is_up else "#FF5252"
    fill = "rgba(0,200,5,0.15)" if is_up else "rgba(255,82,82,0.15)"

    v_min, v_max = min(values), max(values)
    v_range = v_max - v_min
    pad = v_range * 0.1 if v_range > 0 else v_max * 0.01

    fig = go.Figure(
        go.Scatter(
            x=dates,
            y=values,
            mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=fill,
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=SPARKLINE_HEIGHT,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[v_min - pad, v_max + pad]),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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
snapshots_data = fetch_snapshots(days=730)
enriched_stocks_data = fetch_enriched_stocks()
twr_data = fetch_twr()  # YTD TWR (start defaults to Jan 1 of current year)

# Pre-compute values used inside the hero columns
_privacy = _is_privacy()
# Single real-time signal map shared by health score and Signal Alerts.
# Prefers computed_signal (live RSI/bias) over persisted last_scan_signal,
# matching the radar page behaviour.
_enriched_signal_map: dict[str, str] = {
    es["ticker"]: (es.get("computed_signal") or es.get("last_scan_signal", "NORMAL"))
    for es in (enriched_stocks_data or [])
    if es.get("ticker")
}
health_pct, normal_cnt, total_cnt = _compute_health_score(
    stocks_data or [], enriched_signal_map=_enriched_signal_map
)
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
            # YTD Time-Weighted Return
            if twr_data:
                ytd_twr = twr_data.get("twr_pct")
                if ytd_twr is not None:
                    ytd_arrow = "▲" if ytd_twr >= 0 else "▼"
                    ytd_color = "#22c55e" if ytd_twr >= 0 else "#ef4444"
                    st.markdown(
                        f'<p class="hero-delta" style="color:{ytd_color}">'
                        f'{t("dashboard.ytd_return")} {ytd_arrow}{abs(ytd_twr):.2f}%</p>',
                        unsafe_allow_html=True,
                    )
            # Mini sparkline — 30-day portfolio trend
            if snapshots_data and not _privacy:
                _render_sparkline(snapshots_data)
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
# Section 1.3: YTD Dividend Income
# ---------------------------------------------------------------------------
if rebalance_data and enriched_stocks_data:
    # Build {ticker: ytd_dividend_per_share} from enriched stocks (native currency per share)
    _div_lookup: dict[str, float] = {}
    for _es in enriched_stocks_data:
        _div = _es.get("dividend") or {}
        _ytd_dps = _div.get("ytd_dividend_per_share")
        if _ytd_dps is not None and _ytd_dps > 0:
            _div_lookup[_es["ticker"]] = _ytd_dps

    # Compute actual YTD dividend income: shares × ytd_div_per_share × fx_to_display_currency
    _ytd_div_income = 0.0
    for _h in rebalance_data.get("holdings_detail", []):
        _ytd_dps = _div_lookup.get(_h["ticker"])
        if _ytd_dps:
            _fx = _h.get("fx", 1.0)
            _ytd_div_income += _h.get("quantity", 0) * _ytd_dps * _fx

    if _ytd_div_income > 0:
        _div_col, _ = st.columns([1, 3])
        with _div_col:
            _ytd_div_str = PRIVACY_MASK if _privacy else f"${_ytd_div_income:,.2f}"
            st.metric(
                t("dashboard.ytd_dividend"),
                _ytd_div_str,
                help=t("dashboard.ytd_dividend_actual"),
            )


# ---------------------------------------------------------------------------
# Section 1.5: Portfolio Performance Chart
# ---------------------------------------------------------------------------
st.subheader(t("dashboard.performance_title"))

with st.container(border=True):
    if snapshots_data:
        _render_performance_chart(snapshots_data)
    else:
        st.caption(t("dashboard.performance_no_data"))


# ---------------------------------------------------------------------------
# Section 2: Signal Alerts (Action Required — before Allocation)
# ---------------------------------------------------------------------------


def _resolve_signal(s: dict, signal_map: dict[str, str]) -> str:
    """Return the best available signal for a stock.

    Prefers real-time computed_signal from the enriched map; falls back to the
    persisted last_scan_signal field on the stock dict.
    """
    return signal_map.get(s.get("ticker", ""), s.get("last_scan_signal", "NORMAL"))


def _render_signal_rows(stock_list: list, signal_map: dict[str, str]) -> None:
    """Render a column-aligned list of stocks with their resolved signal icons."""
    cat_labels_map = get_category_labels()
    for s in stock_list:
        signal = _resolve_signal(s, signal_map)
        icon = SCAN_SIGNAL_ICONS.get(signal, "⚪")
        cat_short = cat_labels_map.get(s.get("category", ""), s.get("category", "")).split("(")[0].strip()
        _a_icon, _a_ticker, _a_cat, _a_signal = st.columns([0.5, 2, 2, 2])
        with _a_icon:
            st.markdown(icon)
        with _a_ticker:
            st.markdown(f"**{s['ticker']}**")
        with _a_cat:
            st.markdown(cat_short)
        with _a_signal:
            st.markdown(f"`{signal}`")


st.subheader(t("dashboard.signal_alerts_title"))

with st.container(border=True):
    if stocks_data:
        _active_stocks = [s for s in stocks_data if s.get("is_active", True)]
        buy_stocks = [
            s for s in _active_stocks
            if _resolve_signal(s, _enriched_signal_map) in BUY_OPPORTUNITY_SIGNALS
        ]
        risk_stocks = [
            s for s in _active_stocks
            if _resolve_signal(s, _enriched_signal_map) in RISK_WARNING_SIGNALS
        ]

        if buy_stocks or risk_stocks:
            if buy_stocks:
                st.caption(t("dashboard.signal_buy_title"))
                _render_signal_rows(buy_stocks, _enriched_signal_map)

            if risk_stocks:
                if buy_stocks:
                    st.divider()
                st.caption(t("dashboard.signal_risk_title"))
                _render_signal_rows(risk_stocks, _enriched_signal_map)

                # Rebalance advice inline — only shown alongside risk warnings
                advice = rebalance_data.get("advice", []) if rebalance_data else []
                if advice:
                    st.divider()
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
st.subheader(t("dashboard.top_holdings_title", limit=DASHBOARD_TOP_HOLDINGS_LIMIT))

if rebalance_data and rebalance_data.get("holdings_detail"):
    holdings_detail = rebalance_data["holdings_detail"]
    # Sort by weight descending
    sorted_holdings = sorted(holdings_detail, key=lambda h: h.get("weight_pct", 0), reverse=True)
    top_holdings = sorted_holdings[:DASHBOARD_TOP_HOLDINGS_LIMIT]

    privacy = _is_privacy()

    if top_holdings:
        col_ticker = t("dashboard.holdings_table.ticker")
        col_cat = t("dashboard.holdings_table.category")
        col_weight = t("dashboard.holdings_table.weight")
        col_value = t("dashboard.holdings_table.market_value")
        col_change = t("dashboard.holdings_table.daily_change")
        col_total_return = t("dashboard.holdings_table.total_return")
        col_gain_loss = t("dashboard.holdings_table.gain_loss")

        header_row = (
            f"<tr>"
            f"<th style='text-align:left;padding:4px 8px'>{col_ticker}</th>"
            f"<th style='text-align:left;padding:4px 8px'>{col_cat}</th>"
            f"<th style='text-align:right;padding:4px 8px'>{col_weight}</th>"
            f"<th style='text-align:right;padding:4px 8px'>{col_value}</th>"
            f"<th style='text-align:right;padding:4px 8px'>{col_change}</th>"
            f"<th style='text-align:right;padding:4px 8px'>{col_total_return}</th>"
            f"<th style='text-align:right;padding:4px 8px'>{col_gain_loss}</th>"
            f"</tr>"
        )
        data_rows = []
        for h in top_holdings:
            cat = h.get("category", "")
            icon = CATEGORY_ICON_SHORT.get(cat, "")
            change_pct = h.get("change_pct")
            if change_pct is not None:
                arrow = "▲" if change_pct >= 0 else "▼"
                color = "#22c55e" if change_pct >= 0 else "#ef4444"
                change_cell = (
                    f"<td style='text-align:right;padding:4px 8px;"
                    f"color:{color};font-weight:500'>{arrow}{abs(change_pct):.2f}%</td>"
                )
            else:
                change_cell = "<td style='text-align:right;padding:4px 8px'>N/A</td>"

            market_value = h.get("market_value", 0)
            cost_total = h.get("cost_total")
            if cost_total is not None and cost_total > 0:
                gain_loss_amt = market_value - cost_total
                total_return_pct = (gain_loss_amt / cost_total) * 100
                ret_arrow = "▲" if total_return_pct >= 0 else "▼"
                ret_color = "#22c55e" if total_return_pct >= 0 else "#ef4444"
                total_return_cell = (
                    f"<td style='text-align:right;padding:4px 8px;"
                    f"color:{ret_color};font-weight:500'>"
                    f"{ret_arrow}{abs(total_return_pct):.1f}%</td>"
                )
                if privacy:
                    gain_loss_cell = (
                        f"<td style='text-align:right;padding:4px 8px;"
                        f"color:{ret_color}'>{PRIVACY_MASK}</td>"
                    )
                else:
                    sign = "+" if gain_loss_amt >= 0 else "-"
                    gain_loss_cell = (
                        f"<td style='text-align:right;padding:4px 8px;"
                        f"color:{ret_color}'>{sign}${abs(gain_loss_amt):,.0f}</td>"
                    )
            else:
                total_return_cell = "<td style='text-align:right;padding:4px 8px'>—</td>"
                gain_loss_cell = "<td style='text-align:right;padding:4px 8px'>—</td>"

            value_str = PRIVACY_MASK if privacy else f"${market_value:,.2f}"
            data_rows.append(
                f"<tr style='border-top:1px solid rgba(128,128,128,0.15)'>"
                f"<td style='padding:4px 8px'><b>{h.get('ticker', '')}</b></td>"
                f"<td style='padding:4px 8px'>{icon} {cat}</td>"
                f"<td style='text-align:right;padding:4px 8px'>{h.get('weight_pct', 0):.1f}%</td>"
                f"<td style='text-align:right;padding:4px 8px'>{value_str}</td>"
                f"{change_cell}"
                f"{total_return_cell}"
                f"{gain_loss_cell}"
                f"</tr>"
            )

        table_html = (
            "<table style='width:100%;border-collapse:collapse;font-size:0.88rem'>"
            f"<thead style='opacity:0.6'>{header_row}</thead>"
            f"<tbody>{''.join(data_rows)}</tbody>"
            "</table>"
        )
        with st.container(border=True):
            st.markdown(table_html, unsafe_allow_html=True)
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
_sm_hdr, _sm_btn_col = st.columns([3, 1])
with _sm_hdr:
    st.subheader(t("dashboard.resonance.title"))
with _sm_btn_col:
    if st.button(t("dashboard.resonance.goto_smart_money"), use_container_width=True, key="sm_btn_top"):
        st.switch_page("views/smart_money.py")

_great_minds = fetch_great_minds()

if _great_minds is None:
    st.caption(t("dashboard.resonance.unavailable"))
else:
    _gm_stocks = _great_minds.get("stocks", [])
    _gm_total = _great_minds.get("total_count", 0)

    if _gm_total == 0:
        st.info(t("dashboard.resonance.empty"))
    else:
        # Always-visible KPI metrics
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

        # Per-stock detail cards — collapsed by default
        with st.expander(t("dashboard.resonance.details_expander"), expanded=False):
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
