"""
Folio — Smart Money Dashboard (大師足跡追踪).

Tracks SEC 13F filings for institutional investors ("gurus") and surfaces
portfolio resonance with the user's own watchlist / holdings.

Layout:
  Tab bar  : Overview (default) · Per-guru tabs (one per active guru) · Add Guru
  Overview : Guru status cards · Season highlights · Consensus stocks · Sector chart
  Per-guru : Filing meta + metrics · Holding Changes · Top Holdings · Great Minds
  Add Guru : Form to register a new guru by CIK
"""

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from config import (
    HOLDING_ACTION_COLORS,
    HOLDING_ACTION_ICONS,
    SEASON_HIGHLIGHTS_DISPLAY_LIMIT,
    SMART_MONEY_STALE_DAYS,
    SMART_MONEY_TOP_N,
    get_holding_action_label,
)
from i18n import t
from utils import (
    add_guru,
    fetch_great_minds,
    fetch_guru_dashboard,
    fetch_guru_filing,
    fetch_guru_filings,
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
    """Format holding value in $K / $M / $B."""
    if v is None:
        return "N/A"
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.2f}B"
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


def _is_stale(report_date_str: str | None) -> bool:
    if not report_date_str:
        return True
    try:
        rd = date.fromisoformat(report_date_str)
        return (date.today() - rd).days > SMART_MONEY_STALE_DAYS
    except ValueError:
        return True


def _render_sync_button(guru_id: int, button_key: str, label_key: str = "smart_money.overview.sync_button") -> None:
    """Render a sync button for a guru and handle the result in-place."""
    if st.button(t(label_key), key=button_key, use_container_width=True):
        with st.spinner(t("smart_money.sidebar.syncing")):
            result = sync_guru(guru_id)
        if result:
            status = result.get("status", "error")
            if status == "synced":
                st.success(t("smart_money.sidebar.sync_success"))
            elif status == "skipped":
                st.info(t("smart_money.sidebar.sync_skipped"))
            else:
                st.error(t("smart_money.sidebar.sync_error", msg=result.get("message", "")))
            invalidate_guru_caches()
            refresh_ui()
        else:
            st.error(t("common.error_backend"))


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

with st.expander(t("smart_money.sop.title"), expanded=False):
    st.markdown(t("smart_money.sop.content"))

# ---------------------------------------------------------------------------
# Data: Guru List
# ---------------------------------------------------------------------------

gurus = fetch_gurus() or []

# ---------------------------------------------------------------------------
# Build Tab Bar
# ---------------------------------------------------------------------------
# Tabs: [Overview] [Guru 1] [Guru 2] ... [Guru N] [Add Guru]

_tab_labels = [t("smart_money.overview.tab")]
for g in gurus:
    _tab_labels.append(g["display_name"])
_tab_labels.append(t("smart_money.overview.add_guru_tab"))

_tabs = st.tabs(_tab_labels)

# Indices
_overview_tab = _tabs[0]
_guru_tabs = _tabs[1 : 1 + len(gurus)]
_add_guru_tab = _tabs[-1]


# ===========================================================================
# Overview Tab
# ===========================================================================

with _overview_tab:
    dashboard = fetch_guru_dashboard()

    if dashboard is None or not dashboard.get("gurus"):
        st.info(t("smart_money.overview.no_data"))
    else:
        # ---------------------------------------------------------------
        # Guru Status Cards  (N1: batch into rows of 3)
        # ---------------------------------------------------------------
        st.markdown(f"**{t('smart_money.overview.guru_cards_header')}**")

        guru_summaries = dashboard.get("gurus", [])
        # Build a lookup by id for robust matching (S3)
        gurus_by_id = {g["id"]: g for g in gurus}

        for row_start in range(0, len(guru_summaries), 3):
            row_items = guru_summaries[row_start : row_start + 3]
            cols = st.columns(3)
            for i, gs in enumerate(row_items):
                with cols[i]:
                    report_date = gs.get("latest_report_date")
                    stale = _is_stale(report_date)
                    border_color = "#ef4444" if stale else "#22c55e"
                    status_label = (
                        t("smart_money.overview.stale_label")
                        if stale
                        else t("smart_money.overview.recent_label")
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"<span style='font-weight:700;font-size:1.05rem'>"
                            f"{gs['display_name']}</span>"
                            f"&nbsp;<span style='color:{border_color};font-size:0.8rem'>"
                            f"{status_label}</span>",
                            unsafe_allow_html=True,
                        )
                        m1, m2 = st.columns(2)
                        with m1:
                            st.metric(
                                t("smart_money.overview.total_value_label"),
                                _fmt_value(gs.get("total_value")),
                            )
                            st.metric(
                                t("smart_money.overview.report_date_label"),
                                report_date or "N/A",
                            )
                        with m2:
                            st.metric(
                                t("smart_money.overview.holdings_count_label"),
                                gs.get("holdings_count", 0),
                            )
                            st.metric(
                                t("smart_money.overview.filing_count_label"),
                                gs.get("filing_count", 0),
                            )
                        # Per-card sync: match by id (S3)
                        guru_obj = gurus_by_id.get(gs.get("id"))
                        if guru_obj:
                            _render_sync_button(
                                guru_obj["id"],
                                button_key=f"ov_sync_{gs['id']}",
                            )

        st.divider()

        # ---------------------------------------------------------------
        # Season Highlights
        # ---------------------------------------------------------------
        st.markdown(f"**{t('smart_money.overview.highlights_header')}**")
        highlights = dashboard.get("season_highlights", {})
        new_pos = highlights.get("new_positions", [])
        sold_outs = highlights.get("sold_outs", [])

        if not new_pos and not sold_outs:
            st.info(t("smart_money.overview.highlights_empty"))
        else:
            # Sort by value descending for both categories
            new_pos_sorted = sorted(new_pos, key=lambda x: x.get("value", 0.0), reverse=True)
            sold_outs_sorted = sorted(sold_outs, key=lambda x: x.get("value", 0.0), reverse=True)
            
            # Calculate summary metrics
            total_new_value = sum(item.get("value", 0.0) for item in new_pos)
            
            # Summary metrics row
            sum_col1, sum_col2, sum_col3 = st.columns(3)
            with sum_col1:
                st.metric(
                    t("smart_money.overview.highlights_new_count"),
                    len(new_pos),
                )
            with sum_col2:
                st.metric(
                    t("smart_money.overview.highlights_sold_count"),
                    len(sold_outs),
                )
            with sum_col3:
                st.metric(
                    t("smart_money.overview.highlights_total_value"),
                    _fmt_value(total_new_value),
                )
            
            st.divider()
            
            # Two-column layout for new positions and sold-outs
            h_col1, h_col2 = st.columns(2)
            
            with h_col1:
                st.markdown(
                    f"<span style='color:#22c55e;font-weight:600;font-size:1.1rem'>"
                    f"🟢 {t('smart_money.overview.new_positions_header')} ({len(new_pos)})"
                    f"</span>",
                    unsafe_allow_html=True,
                )
                
                # Display top N items
                display_items = new_pos_sorted[:SEASON_HIGHLIGHTS_DISPLAY_LIMIT]
                for item in display_items:
                    ticker = item.get("ticker") or "—"
                    company = item.get("company_name", "")
                    guru_name = item.get("guru_display_name", "")
                    value = _fmt_value(item.get("value"))
                    weight = item.get("weight_pct")
                    
                    with st.container(border=True):
                        t_col, v_col = st.columns([3, 1])
                        with t_col:
                            st.markdown(f"**{ticker}**")
                            st.caption(company if company else guru_name)
                        with v_col:
                            st.metric("", value)
                            if weight:
                                st.caption(f"{weight:.1f}%")
                        st.caption(f"👤 {guru_name}")
                
                # Show remaining items in expander if there are more
                if len(new_pos_sorted) > SEASON_HIGHLIGHTS_DISPLAY_LIMIT:
                    with st.expander(
                        t("smart_money.overview.highlights_show_all", 
                          count=len(new_pos_sorted) - SEASON_HIGHLIGHTS_DISPLAY_LIMIT),
                        expanded=False
                    ):
                        for item in new_pos_sorted[SEASON_HIGHLIGHTS_DISPLAY_LIMIT:]:
                            ticker = item.get("ticker") or "—"
                            company = item.get("company_name", "")
                            guru_name = item.get("guru_display_name", "")
                            value = _fmt_value(item.get("value"))
                            weight = item.get("weight_pct")
                            weight_str = f" · {weight:.1f}%" if weight else ""
                            st.markdown(
                                f"**{ticker}** — {guru_name} · {value}{weight_str}"
                            )
                            if company:
                                st.caption(company)
            
            with h_col2:
                st.markdown(
                    f"<span style='color:#ef4444;font-weight:600;font-size:1.1rem'>"
                    f"🔴 {t('smart_money.overview.sold_outs_header')} ({len(sold_outs)})"
                    f"</span>",
                    unsafe_allow_html=True,
                )
                
                # Display top N items
                display_items = sold_outs_sorted[:SEASON_HIGHLIGHTS_DISPLAY_LIMIT]
                for item in display_items:
                    ticker = item.get("ticker") or "—"
                    company = item.get("company_name", "")
                    guru_name = item.get("guru_display_name", "")
                    value = _fmt_value(item.get("value"))
                    
                    with st.container(border=True):
                        t_col, v_col = st.columns([3, 1])
                        with t_col:
                            st.markdown(f"**{ticker}**")
                            st.caption(company if company else guru_name)
                        with v_col:
                            st.metric("", value)
                        st.caption(f"👤 {guru_name}")
                
                # Show remaining items in expander if there are more
                if len(sold_outs_sorted) > SEASON_HIGHLIGHTS_DISPLAY_LIMIT:
                    with st.expander(
                        t("smart_money.overview.highlights_show_all",
                          count=len(sold_outs_sorted) - SEASON_HIGHLIGHTS_DISPLAY_LIMIT),
                        expanded=False
                    ):
                        for item in sold_outs_sorted[SEASON_HIGHLIGHTS_DISPLAY_LIMIT:]:
                            ticker = item.get("ticker") or "—"
                            company = item.get("company_name", "")
                            guru_name = item.get("guru_display_name", "")
                            value = _fmt_value(item.get("value"))
                            st.markdown(
                                f"**{ticker}** — {guru_name} · {value}"
                            )
                            if company:
                                st.caption(company)

        st.divider()

        # ---------------------------------------------------------------
        # Consensus Stocks
        # ---------------------------------------------------------------
        st.markdown(f"**{t('smart_money.overview.consensus_header')}**")
        consensus = dashboard.get("consensus", [])

        if not consensus:
            st.info(t("smart_money.overview.consensus_empty"))
        else:
            for item in consensus:
                ticker = item.get("ticker", "—")
                guru_count = item.get("guru_count", 0)
                guru_names = item.get("gurus", [])
                with st.container(border=True):
                    c_t, c_g, c_v = st.columns([1.5, 4, 1.5])
                    with c_t:
                        st.markdown(f"### {ticker}")
                    with c_g:
                        st.caption(
                            f"{t('smart_money.overview.consensus_gurus')}: "
                            + ", ".join(guru_names)
                        )
                    with c_v:
                        st.metric(t("smart_money.great_minds.guru_count_label"), guru_count)

        st.divider()

        # ---------------------------------------------------------------
        # Sector Allocation (horizontal bar chart)
        # ---------------------------------------------------------------
        st.markdown(f"**{t('smart_money.overview.sector_header')}**")
        sector_data = dashboard.get("sector_breakdown", [])

        if not sector_data:
            st.info(t("smart_money.overview.sector_empty"))
        else:
            sectors = [s["sector"] for s in sector_data]
            weights = [s["weight_pct"] for s in sector_data]
            counts = [s["holding_count"] for s in sector_data]

            fig = go.Figure(
                go.Bar(
                    x=weights[::-1],
                    y=sectors[::-1],
                    orientation="h",
                    marker_color="#3B82F6",
                    text=[f"{w:.1f}%" for w in weights[::-1]],
                    textposition="outside",
                    customdata=counts[::-1],
                    hovertemplate="%{y}: %{x:.1f}% (%{customdata} holdings)<extra></extra>",
                )
            )
            fig.update_layout(
                height=max(250, len(sectors) * 28),
                margin=dict(l=0, r=60, t=10, b=10),
                xaxis=dict(title=t("smart_money.overview.sector_weight_axis"), showgrid=True),  # S4
                yaxis=dict(showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ===========================================================================
# Per-Guru Tabs
# ===========================================================================

for tab_widget, guru in zip(_guru_tabs, gurus):
    with tab_widget:
        guru_id = guru["id"]
        guru_name = guru["display_name"]

        # --- Sync button in tab header area ---
        _hdr_col, _sync_col = st.columns([5, 1])
        with _hdr_col:
            st.subheader(guru_name)
        with _sync_col:
            _render_sync_button(
                guru_id,
                button_key=f"guru_sync_{guru_id}",
                label_key="smart_money.sidebar.sync_button",
            )

        # --- Filing Data ---
        filing = fetch_guru_filing(guru_id)

        if filing is None:
            st.warning(t("smart_money.no_filing", guru=guru_name))
            continue

        report_date = filing.get("report_date", "N/A")
        filing_date = filing.get("filing_date", "N/A")
        filing_url = filing.get("filing_url", "")
        total_value = filing.get("total_value")
        holdings_count = filing.get("holdings_count", 0)

        # Lagging indicator banner
        st.warning(
            t(
                "smart_money.lagging_banner",
                report_date=report_date,
                filing_date=filing_date,
            )
        )

        # Filing meta metrics
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

        # --- Filing history mini-timeline ---
        filings_history = fetch_guru_filings(guru_id) or []
        if len(filings_history) > 1:
            with st.expander(
                t("smart_money.overview.filing_history_expander", count=len(filings_history)),
                expanded=False,
            ):
                for fh in filings_history:
                    fh_report = fh.get("report_date", "—")
                    fh_filed = fh.get("filing_date", "—")
                    fh_val = _fmt_value(fh.get("total_value"))
                    fh_count = fh.get("holdings_count", 0)
                    st.caption(
                        t(
                            "smart_money.overview.filing_history_row",
                            report_date=fh_report,
                            filing_date=fh_filed,
                            total_value=fh_val,
                            holdings_count=fh_count,
                        )
                    )

        st.divider()

        # --- Sections (expanders instead of nested tabs to avoid Streamlit setIn bug) ---

        # ===================================================================
        # Section: Holding Changes
        # ===================================================================

        with st.expander(t("smart_money.tab.changes"), expanded=True):
            changed = fetch_guru_holding_changes(guru_id, limit=20) or []
            
            # Total change counts from filing summary
            new_count = filing.get("new_positions", 0)
            sold_count = filing.get("sold_out", 0)
            inc_count = filing.get("increased", 0)
            dec_count = filing.get("decreased", 0)
            total_changes = new_count + sold_count + inc_count + dec_count

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
            
            # Show note about top 20 focus if there are more changes
            if total_changes > 20:
                st.info(
                    t("smart_money.changes.top_20_note", 
                      shown=len(changed), total=total_changes)
                )

            st.divider()

            if not changed:
                st.info(t("smart_money.changes.no_changes"))
            else:
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

        # ===================================================================
        # Section: Top Holdings
        # ===================================================================

        with st.expander(t("smart_money.tab.top"), expanded=True):
            top_n = fetch_guru_top_holdings(guru_id, n=SMART_MONEY_TOP_N)

            if not top_n:
                st.info(t("smart_money.top.no_data"))
            else:
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
                st.plotly_chart(
                    fig, use_container_width=True, config={"displayModeBar": False}
                )

                st.divider()

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
                            f"<span style='color:{HOLDING_ACTION_COLORS.get(action, '#9CA3AF')}'>"
                            f"{_action_badge(action)}</span>"
                        )
                        st.markdown(badge_html, unsafe_allow_html=True)
                    with c_w:
                        st.caption(f"{weight:.1f}%" if weight is not None else "—")
                    with c_v:
                        st.caption(value)
                    with c_s:
                        st.caption(shares)

        # ===================================================================
        # Section: Great Minds
        # ===================================================================

        with st.expander(t("smart_money.tab.great_minds"), expanded=False):
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

                        guru_actions = " · ".join(
                            f"{g.get('guru_display_name','?')}: {_action_badge(g.get('action','UNCHANGED'))}"
                            for g in item_gurus
                        )
                        guru_names = ", ".join(
                            g.get("guru_display_name", "?") for g in item_gurus
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


# ===========================================================================
# Add Guru Tab
# ===========================================================================

with _add_guru_tab:
    st.subheader(t("smart_money.add_guru.title"))
    st.caption(t("smart_money.add_guru.description"))

    new_name = st.text_input(
        t("smart_money.add_guru.name_label"),
        key="sm_new_guru_name",
        placeholder=t("smart_money.add_guru.name_placeholder"),
    )
    new_cik = st.text_input(
        t("smart_money.add_guru.cik_label"),
        key="sm_new_guru_cik",
        placeholder=t("smart_money.add_guru.cik_placeholder"),
    )
    new_display = st.text_input(
        t("smart_money.add_guru.display_label"),
        key="sm_new_guru_display",
        placeholder=t("smart_money.add_guru.display_placeholder"),
    )
    if st.button(
        t("smart_money.add_guru.submit_button"),
        key="sm_add_guru_btn",
        use_container_width=True,
    ):
        if not new_name.strip() or not new_cik.strip() or not new_display.strip():
            st.warning(t("smart_money.add_guru.required_warning"))
        else:
            result = add_guru(new_name.strip(), new_cik.strip(), new_display.strip())
            if result:
                st.success(
                    t(
                        "smart_money.add_guru.success",
                        display_name=result["display_name"],
                    )
                )
                invalidate_guru_caches()
                refresh_ui()
            else:
                st.error(t("common.error_backend"))
