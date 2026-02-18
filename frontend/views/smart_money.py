"""
Folio — Smart Money Dashboard (大師足跡追踪).

Tracks SEC 13F filings for institutional investors ("gurus") and surfaces
portfolio resonance with the user's own watchlist / holdings.

Layout:
  Sidebar  : Guru selector · Sync button · Add Guru expander
  Tab 1    : Holding Changes (NEW / SOLD / INCREASED / DECREASED)
  Tab 2    : Top 10 Holdings (weight bar chart + table)
  Tab 3    : Great Minds Think Alike (resonance list)
"""

import plotly.graph_objects as go
import streamlit as st

from config import (
    HOLDING_ACTION_COLORS,
    HOLDING_ACTION_ICONS,
    SMART_MONEY_TOP_N,
    get_holding_action_label,
)
from i18n import t
from utils import (
    add_guru,
    fetch_great_minds,
    fetch_guru_filing,
    fetch_guru_holding_changes,
    fetch_guru_top_holdings,
    fetch_gurus,
    invalidate_guru_caches,
    refresh_ui,
    sync_guru,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _action_badge(action: str) -> str:
    icon = HOLDING_ACTION_ICONS.get(action, "⚪")
    label = get_holding_action_label(action)
    return f"{icon} {label}"


def _fmt_value(v: float | None) -> str:
    """Format holding value in $K (thousands) or $M (millions)."""
    if v is None:
        return "N/A"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.1f}K"
    return f"${v:.0f}"


def _fmt_shares(s: float | None) -> str:
    if s is None:
        return "N/A"
    if s >= 1_000_000:
        return f"{s / 1_000_000:.2f}M"
    if s >= 1_000:
        return f"{s / 1_000:.1f}K"
    return f"{s:.0f}"


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------

_title_col, _refresh_col = st.columns([6, 1])
with _title_col:
    st.title(t("smart_money.title"))
    st.caption(t("smart_money.caption"))
with _refresh_col:
    if st.button(t("common.refresh"), use_container_width=True):
        invalidate_guru_caches()
        refresh_ui()

# ---------------------------------------------------------------------------
# Data: Guru List
# ---------------------------------------------------------------------------

gurus = fetch_gurus() or []

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header(t("smart_money.sidebar.header"))

    if not gurus:
        st.warning(t("smart_money.sidebar.no_gurus"))
        selected_guru = None
    else:
        guru_options = {g["display_name"]: g for g in gurus}
        selected_name = st.selectbox(
            t("smart_money.sidebar.guru_selector"),
            options=list(guru_options.keys()),
            key="sm_guru_selector",
        )
        selected_guru = guru_options[selected_name]

    st.divider()

    # Sync button
    if selected_guru:
        if st.button(
            t("smart_money.sidebar.sync_button"),
            use_container_width=True,
            help=t("smart_money.sidebar.sync_help"),
        ):
            with st.spinner(t("smart_money.sidebar.syncing")):
                result = sync_guru(selected_guru["id"])
            if result:
                status = result.get("status", "error")
                if status == "synced":
                    st.success(t("smart_money.sidebar.sync_success"))
                elif status == "skipped":
                    st.info(t("smart_money.sidebar.sync_skipped"))
                else:
                    st.error(
                        t(
                            "smart_money.sidebar.sync_error",
                            msg=result.get("message", ""),
                        )
                    )
                invalidate_guru_caches()
                refresh_ui()
            else:
                st.error(t("common.error_backend"))

    st.divider()

    # Add Guru expander
    with st.expander(t("smart_money.sidebar.add_guru_title"), expanded=False):
        new_name = st.text_input(
            t("smart_money.sidebar.add_name"),
            key="sm_new_guru_name",
            placeholder=t("smart_money.sidebar.add_name_placeholder"),
        )
        new_cik = st.text_input(
            t("smart_money.sidebar.add_cik"),
            key="sm_new_guru_cik",
            placeholder="0001067983",
        )
        new_display = st.text_input(
            t("smart_money.sidebar.add_display_name"),
            key="sm_new_guru_display",
            placeholder=t("smart_money.sidebar.add_display_placeholder"),
        )
        if st.button(
            t("smart_money.sidebar.add_button"),
            key="sm_add_guru_btn",
            use_container_width=True,
        ):
            if not new_name.strip() or not new_cik.strip() or not new_display.strip():
                st.warning(t("smart_money.sidebar.add_required"))
            else:
                result = add_guru(
                    new_name.strip(), new_cik.strip(), new_display.strip()
                )
                if result:
                    st.success(
                        t(
                            "smart_money.sidebar.add_success",
                            display_name=result["display_name"],
                        )
                    )
                    invalidate_guru_caches()
                    refresh_ui()
                else:
                    st.error(t("common.error_backend"))

# ---------------------------------------------------------------------------
# No guru selected — stop early
# ---------------------------------------------------------------------------

if not selected_guru:
    st.info(t("smart_money.no_gurus_hint"))
    st.stop()

guru_id = selected_guru["id"]
guru_name = selected_guru["display_name"]

# ---------------------------------------------------------------------------
# Filing Data + Lagging Indicator Banner
# ---------------------------------------------------------------------------

filing = fetch_guru_filing(guru_id)

if filing is None:
    st.warning(t("smart_money.no_filing", guru=guru_name))
    st.stop()

report_date = filing.get("report_date", "N/A")
filing_date = filing.get("filing_date", "N/A")
filing_url = filing.get("filing_url", "")
total_value = filing.get("total_value")
holdings_count = filing.get("holdings_count", 0)

st.warning(
    t(
        "smart_money.lagging_banner",
        report_date=report_date,
        filing_date=filing_date,
    )
)

# Filing meta row
_m1, _m2, _m3, _m4 = st.columns(4)
with _m1:
    st.metric(t("smart_money.metric.report_date"), report_date)
with _m2:
    st.metric(t("smart_money.metric.filing_date"), filing_date)
with _m3:
    tv_label = _fmt_value(total_value) if total_value else "N/A"
    st.metric(t("smart_money.metric.total_value"), tv_label)
with _m4:
    st.metric(t("smart_money.metric.holdings_count"), holdings_count)

if filing_url:
    st.link_button(
        t("smart_money.edgar_link"),
        url=filing_url,
        help=t("smart_money.edgar_link_help"),
    )

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_changes, tab_top, tab_great_minds = st.tabs(
    [
        t("smart_money.tab.changes"),
        t("smart_money.tab.top"),
        t("smart_money.tab.great_minds"),
    ]
)

# ===========================================================================
# Tab 1 — Holding Changes
# ===========================================================================

with tab_changes:
    # Use the dedicated /holdings endpoint — returns ALL action != UNCHANGED,
    # not just the top-10 weight slice from the filing summary.
    changed = fetch_guru_holding_changes(guru_id) or []

    new_count = filing.get("new_positions", 0)
    sold_count = filing.get("sold_out", 0)
    inc_count = filing.get("increased", 0)
    dec_count = filing.get("decreased", 0)

    # Summary metrics row
    _c1, _c2, _c3, _c4 = st.columns(4)
    with _c1:
        st.metric(
            f"{HOLDING_ACTION_ICONS['NEW_POSITION']} {t('smart_money.action.new_position')}",
            new_count,
        )
    with _c2:
        st.metric(
            f"{HOLDING_ACTION_ICONS['SOLD_OUT']} {t('smart_money.action.sold_out')}",
            sold_count,
        )
    with _c3:
        st.metric(
            f"{HOLDING_ACTION_ICONS['INCREASED']} {t('smart_money.action.increased')}",
            inc_count,
        )
    with _c4:
        st.metric(
            f"{HOLDING_ACTION_ICONS['DECREASED']} {t('smart_money.action.decreased')}",
            dec_count,
        )

    st.divider()

    if not changed:
        st.info(t("smart_money.changes.no_changes"))
    else:
        # Group by action for visual clarity
        action_order = ["NEW_POSITION", "SOLD_OUT", "INCREASED", "DECREASED"]
        grouped: dict[str, list] = {a: [] for a in action_order}
        for h in changed:
            action = h.get("action", "UNCHANGED")
            if action in grouped:
                grouped[action].append(h)

        for action in action_order:
            items = grouped[action]
            if not items:
                continue

            color = HOLDING_ACTION_COLORS[action]
            badge = _action_badge(action)
            st.markdown(
                f"<span style='color:{color};font-size:1rem;font-weight:600'>"
                f"{badge} ({len(items)})</span>",
                unsafe_allow_html=True,
            )

            for h in items:
                ticker = h.get("ticker") or h.get("cusip", "—")
                company = h.get("company_name", "")
                value = _fmt_value(h.get("value"))
                shares = _fmt_shares(h.get("shares"))
                change_pct = h.get("change_pct")
                weight_pct = h.get("weight_pct")

                col_t, col_c, col_v, col_s, col_chg, col_w = st.columns(
                    [1.5, 3, 1.5, 1.5, 1.5, 1.5]
                )
                with col_t:
                    st.markdown(f"**{ticker}**")
                with col_c:
                    st.caption(company)
                with col_v:
                    st.caption(f"{t('smart_money.col.value')}: {value}")
                with col_s:
                    st.caption(f"{t('smart_money.col.shares')}: {shares}")
                with col_chg:
                    if change_pct is not None:
                        sign = "+" if change_pct > 0 else ""
                        st.caption(f"Δ {sign}{change_pct:.1f}%")
                    else:
                        st.caption("—")
                with col_w:
                    if weight_pct is not None:
                        st.caption(f"{weight_pct:.1f}%")
                    else:
                        st.caption("—")

            st.markdown("---")

# ===========================================================================
# Tab 2 — Top Holdings
# ===========================================================================

with tab_top:
    top_n = fetch_guru_top_holdings(guru_id, n=SMART_MONEY_TOP_N)

    if not top_n:
        st.info(t("smart_money.top.no_data"))
    else:
        # Build bar chart
        tickers = [h.get("ticker") or h.get("cusip", "?") for h in top_n]
        weights = [h.get("weight_pct") or 0.0 for h in top_n]
        colors = [
            HOLDING_ACTION_COLORS.get(h.get("action", "UNCHANGED"), "#9CA3AF")
            for h in top_n
        ]

        fig = go.Figure(
            go.Bar(
                x=weights[::-1],
                y=tickers[::-1],
                orientation="h",
                marker_color=colors[::-1],
                text=[f"{w:.1f}%" for w in weights[::-1]],
                textposition="outside",
                hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
            )
        )
        fig.update_layout(
            height=max(300, len(top_n) * 32),
            margin=dict(l=0, r=60, t=20, b=20),
            xaxis=dict(title=t("smart_money.top.weight_axis"), showgrid=True),
            yaxis=dict(showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.divider()

        # Detail table
        st.markdown(f"**{t('smart_money.top.table_title')}**")
        for rank, h in enumerate(top_n, start=1):
            ticker = h.get("ticker") or h.get("cusip", "—")
            company = h.get("company_name", "")
            action = h.get("action", "UNCHANGED")
            weight = h.get("weight_pct")
            value = _fmt_value(h.get("value"))
            shares = _fmt_shares(h.get("shares"))

            c_rank, c_tk, c_co, c_act, c_w, c_v, c_s = st.columns(
                [0.5, 1.5, 3, 1.5, 1, 1.5, 1.5]
            )
            with c_rank:
                st.markdown(f"**#{rank}**")
            with c_tk:
                st.markdown(f"**{ticker}**")
            with c_co:
                st.caption(company)
            with c_act:
                badge_html = (
                    f"<span style='color:{HOLDING_ACTION_COLORS.get(action,'#9CA3AF')}'>"
                    f"{_action_badge(action)}</span>"
                )
                st.markdown(badge_html, unsafe_allow_html=True)
            with c_w:
                st.caption(f"{weight:.1f}%" if weight is not None else "—")
            with c_v:
                st.caption(value)
            with c_s:
                st.caption(shares)

# ===========================================================================
# Tab 3 — Great Minds Think Alike
# ===========================================================================

with tab_great_minds:
    st.caption(t("smart_money.great_minds.caption"))

    great_minds_data = fetch_great_minds()

    if great_minds_data is None:
        st.error(t("common.error_backend"))
    else:
        stocks = great_minds_data.get("stocks", [])
        total_count = great_minds_data.get("total_count", 0)

        if total_count == 0:
            st.info(t("smart_money.great_minds.empty"))
        else:
            st.metric(
                t("smart_money.great_minds.overlap_count"),
                total_count,
            )
            st.divider()

            for item in stocks:
                ticker = item.get("ticker", "—")
                guru_count = item.get("guru_count", 0)
                item_gurus = item.get("gurus", [])

                guru_names = ", ".join(
                    g.get("guru_display_name", "?") for g in item_gurus
                )
                guru_actions = " · ".join(
                    f"{g.get('guru_display_name','?')}: {_action_badge(g.get('action','UNCHANGED'))}"
                    for g in item_gurus
                )

                with st.container(border=True):
                    _t_col, _g_col, _a_col = st.columns([2, 1, 4])
                    with _t_col:
                        st.markdown(f"### {ticker}")
                    with _g_col:
                        st.metric(
                            t("smart_money.great_minds.guru_count_label"),
                            guru_count,
                        )
                    with _a_col:
                        st.caption(guru_actions if guru_actions else guru_names)
