"""
FX Watch — 外匯換匯時機監控
提供使用者自訂外匯監控配置，並接收換匯時機警報。
"""

import streamlit as st
from datetime import datetime

from i18n import t
from config import (
    FX_CURRENCY_OPTIONS,
    get_privacy_toggle_label,
)
from utils import (
    create_fx_watch,
    delete_fx_watch,
    fetch_fx_watch_analysis,
    fetch_fx_watches,
    invalidate_fx_watch_caches,
    is_privacy as _is_privacy,
    on_privacy_change as _on_privacy_change,
    patch_fx_watch,
    post_fx_watch_alert,
    post_fx_watch_check,
    refresh_ui as _refresh_ui,
    show_toast,
    toggle_fx_watch,
)


# ---------------------------------------------------------------------------
# Chart Rendering Function
# ---------------------------------------------------------------------------


@st.fragment
def _render_fx_chart(base: str, quote: str, recent_high_days: int, watch_id: int) -> None:
    """
    Render interactive 3-month FX rate trend chart with period selection.

    Args:
        base: Base currency code
        quote: Quote currency code
        recent_high_days: Lookback period for recent high reference line
        watch_id: Unique watch configuration ID (for widget key uniqueness)

    Features:
        - 3-month daily closing rates (full available data)
        - Period selection: 1M/2M/3M via radio buttons
        - Color-coded trend: green (up) / red (down)
        - Reference line for recent high threshold
        - Hover tooltips with 4 decimal precision
    """
    import plotly.graph_objects as go

    from config import (
        FX_CHART_HEIGHT,
        get_fx_chart_periods,
    )
    from utils import fetch_fx_history

    # Fetch data
    fx_data = fetch_fx_history(base, quote)

    if not fx_data or len(fx_data) < 5:
        st.caption(t("fx_watch.chart.insufficient_data"))
        return

    # Period selection (horizontal radio buttons)
    fx_chart_periods = get_fx_chart_periods()
    period_keys = list(fx_chart_periods.keys())
    period_label = st.radio(
        t("fx_watch.chart.period_label"),
        period_keys,
        index=len(period_keys) - 1,
        horizontal=True,
        key=f"fx_chart_period_{watch_id}",
        label_visibility="collapsed",
    )

    # Slice data to selected period (client-side filtering, no re-fetch)
    n_days = fx_chart_periods[period_label]
    sliced = fx_data[-n_days:] if len(fx_data) >= n_days else fx_data

    dates = [d["date"] for d in sliced]
    rates = [d["close"] for d in sliced]

    # Color based on period trend (start vs end)
    is_up = rates[-1] >= rates[0]
    line_color = "#00C805" if is_up else "#FF5252"  # Green / Red
    fill_color = "rgba(0,200,5,0.1)" if is_up else "rgba(255,82,82,0.1)"

    # Create line chart with fill
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=rates,
            mode="lines",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate=t("fx_watch.chart.hover_template", x="%{x}", y="%{y:.4f}"),
        )
    )

    # Add recent high reference line (if sufficient data)
    if len(sliced) >= recent_high_days:
        recent_high = max(d["close"] for d in sliced[-recent_high_days:])
        fig.add_hline(
            y=recent_high,
            line_dash="dash",
            line_color="#FFA500",  # Orange
            annotation_text=t("fx_watch.chart.high_annotation", days=recent_high_days, high=recent_high),
            annotation_position="right",
        )

    # Chart styling (transparent backgrounds, minimal chrome)
    y_min, y_max = min(rates), max(rates)
    padding = (y_max - y_min) * 0.05 if y_max > y_min else y_max * 0.02

    fig.update_layout(
        height=FX_CHART_HEIGHT,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(
            range=[y_min - padding, y_max + padding],
            showgrid=True,
            gridcolor="rgba(128,128,128,0.1)",
        ),
        xaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"fx_chart_{watch_id}",
    )


# ---------------------------------------------------------------------------
# Page Content
# ---------------------------------------------------------------------------

# Title row with privacy toggle
_title_cols = st.columns([4, 1])
with _title_cols[0]:
    st.title(t("fx_watch.title"))
    st.caption(t("fx_watch.caption"))

with _title_cols[1]:
    st.toggle(get_privacy_toggle_label(), key="privacy_mode", on_change=_on_privacy_change)

# Usage manual (collapsible)
with st.expander(t("fx_watch.sop_title")):
    st.markdown(t("fx_watch.sop_content"))

# ---------------------------------------------------------------------------
# Edit Watch Popover
# ---------------------------------------------------------------------------

def edit_watch_popover(watch: dict):
    """Popover for editing watch configuration inline."""
    with st.popover(t("fx_watch.edit.button"), use_container_width=True):
        st.markdown(f"**{t('fx_watch.edit.title', pair=watch['base_currency'] + '/' + watch['quote_currency'])}**")

        # Detection settings
        recent_high_days = st.slider(
            t("fx_watch.form.recent_high_days"),
            min_value=5,
            max_value=90,
            value=watch["recent_high_days"],
            step=5,
            key=f"edit_recent_{watch['id']}"
        )

        consecutive_days = st.slider(
            t("fx_watch.form.consecutive_days"),
            min_value=2,
            max_value=10,
            value=watch["consecutive_increase_days"],
            step=1,
            key=f"edit_consec_{watch['id']}"
        )

        st.divider()

        # Alert toggles
        alert_on_high = st.checkbox(
            t("fx_watch.form.alert_on_high"),
            value=watch["alert_on_recent_high"],
            key=f"edit_high_{watch['id']}"
        )

        alert_on_consecutive = st.checkbox(
            t("fx_watch.form.alert_on_consecutive"),
            value=watch["alert_on_consecutive_increase"],
            key=f"edit_consecutive_{watch['id']}"
        )

        reminder_hours = st.number_input(
            t("fx_watch.form.reminder_hours"),
            min_value=1,
            max_value=168,
            value=watch["reminder_interval_hours"],
            step=1,
            key=f"edit_reminder_{watch['id']}"
        )

        st.divider()

        # Save button
        if st.button(t("fx_watch.form.save"), key=f"save_edit_{watch['id']}", use_container_width=True):
            # Validation
            if not alert_on_high and not alert_on_consecutive:
                st.warning(t("fx_watch.form.error_no_alert"))
            else:
                payload = {
                    "recent_high_days": recent_high_days,
                    "consecutive_increase_days": consecutive_days,
                    "alert_on_recent_high": alert_on_high,
                    "alert_on_consecutive_increase": alert_on_consecutive,
                    "reminder_interval_hours": reminder_hours,
                }

                level, msg = patch_fx_watch(watch["id"], payload)
                show_toast(level, msg)
                if level == "success":
                    invalidate_fx_watch_caches()
                    _refresh_ui()


# ---------------------------------------------------------------------------
# Add Watch Dialog
# ---------------------------------------------------------------------------

@st.dialog(t("fx_watch.dialog.title"), width="large")
def add_watch_dialog():
    """Dialog for adding a new FX watch configuration."""
    with st.form("add_fx_watch_form", clear_on_submit=False):
        col_base, col_quote = st.columns(2)
        with col_base:
            base_currency = st.selectbox(
                t("fx_watch.form.base_currency"),
                options=FX_CURRENCY_OPTIONS,
                index=0,
                help=t("fx_watch.form.base_currency_help"),
                key="add_dialog_base"
            )

        with col_quote:
            quote_currency = st.selectbox(
                t("fx_watch.form.quote_currency"),
                options=FX_CURRENCY_OPTIONS,
                index=1,
                help=t("fx_watch.form.quote_currency_help"),
                key="add_dialog_quote"
            )

        st.divider()

        col_recent, col_consec = st.columns(2)
        with col_recent:
            recent_high_days = st.slider(
                t("fx_watch.form.recent_high_days"),
                min_value=5,
                max_value=90,
                value=30,
                step=5,
                help=t("fx_watch.form.recent_high_days_help")
            )

        with col_consec:
            consecutive_days = st.slider(
                t("fx_watch.form.consecutive_days"),
                min_value=2,
                max_value=10,
                value=3,
                step=1,
                help=t("fx_watch.form.consecutive_days_help")
            )

        st.divider()

        col_toggle1, col_toggle2 = st.columns(2)
        with col_toggle1:
            alert_on_high = st.checkbox(
                t("fx_watch.form.alert_on_high"),
                value=True,
                help=t("fx_watch.form.alert_on_high_help")
            )

        with col_toggle2:
            alert_on_consecutive = st.checkbox(
                t("fx_watch.form.alert_on_consecutive"),
                value=True,
                help=t("fx_watch.form.alert_on_consecutive_help")
            )

        reminder_hours = st.number_input(
            t("fx_watch.form.reminder_hours"),
            min_value=1,
            max_value=168,
            value=24,
            step=1,
            help=t("fx_watch.form.reminder_hours_help")
        )

        st.divider()

        col_submit, col_cancel = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button(t("fx_watch.form.submit"), use_container_width=True, type="primary")
        with col_cancel:
            cancelled = st.form_submit_button(t("fx_watch.form.cancel"), use_container_width=True)

        if cancelled:
            st.session_state["show_add_dialog"] = False
            st.rerun()

        if submitted:
            if base_currency == quote_currency:
                st.error(t("fx_watch.form.error_same_currency"))
            elif not alert_on_high and not alert_on_consecutive:
                st.warning(t("fx_watch.form.error_no_alert"))
            else:
                payload = {
                    "base_currency": base_currency,
                    "quote_currency": quote_currency,
                    "recent_high_days": recent_high_days,
                    "consecutive_increase_days": consecutive_days,
                    "alert_on_recent_high": alert_on_high,
                    "alert_on_consecutive_increase": alert_on_consecutive,
                    "reminder_interval_hours": reminder_hours,
                }

                level, msg = create_fx_watch(payload)
                show_toast(level, msg)
                if level == "success":
                    invalidate_fx_watch_caches()
                    st.session_state["show_add_dialog"] = False
                    st.rerun()

# Main content: Fetch watches
watches = fetch_fx_watches()

# Initialize session state for dialog control
if "show_add_dialog" not in st.session_state:
    st.session_state["show_add_dialog"] = False

# ---------------------------------------------------------------------------
# Top Action Bar: KPI Metrics + Quick Actions (always visible)
# ---------------------------------------------------------------------------

top_row = st.columns([2, 2, 2, 1, 1, 1])

with top_row[0]:
    st.metric(t("fx_watch.metric.total"), len(watches) if watches else 0)

with top_row[1]:
    active_count = sum(1 for w in watches if w.get("is_active", False)) if watches else 0
    st.metric(t("fx_watch.metric.active"), active_count)

with top_row[2]:
    if watches:
        last_times = [
            w.get("last_alerted_at")
            for w in watches
            if w.get("last_alerted_at")
        ]
        if last_times:
            latest = max(last_times)
            st.metric(t("fx_watch.metric.last_alert"), datetime.fromisoformat(latest).strftime("%m/%d %H:%M"))
        else:
            st.metric(t("fx_watch.metric.last_alert"), t("fx_watch.metric.not_sent"))
    else:
        st.metric(t("fx_watch.metric.last_alert"), "—")

with top_row[3]:
    if st.button(t("fx_watch.action.check"), use_container_width=True, help=t("fx_watch.action.check_help"), disabled=not watches):
        with st.spinner(t("fx_watch.action.analyzing")):
            level, msg = post_fx_watch_check()
            show_toast(level, msg)
            if level == "success":
                invalidate_fx_watch_caches()
                _refresh_ui()

with top_row[4]:
    if st.button(t("fx_watch.action.alert"), use_container_width=True, help=t("fx_watch.action.alert_help"), disabled=not watches):
        with st.spinner(t("fx_watch.action.sending")):
            level, msg = post_fx_watch_alert()
            show_toast(level, msg)
            if level == "success":
                invalidate_fx_watch_caches()
                _refresh_ui()

with top_row[5]:
    if st.button(t("fx_watch.action.add"), use_container_width=True, type="primary", help=t("fx_watch.action.add_help")):
        for key in list(st.session_state.keys()):
            if key.startswith("add_dialog_"):
                del st.session_state[key]
        st.session_state["show_add_dialog"] = True
        st.rerun()

st.divider()

if st.session_state.get("show_add_dialog", False):
    add_watch_dialog()

if not watches:
    st.info(t("fx_watch.empty.message"))
    st.caption(t("fx_watch.empty.hint"))
    st.stop()

analysis_map = fetch_fx_watch_analysis()

# ---------------------------------------------------------------------------
# Unified Card Layout (one card per watch)
# ---------------------------------------------------------------------------

st.subheader(t("fx_watch.list.title"))

for watch in watches:
    watch_id = watch["id"]
    pair = f"{watch['base_currency']}/{watch['quote_currency']}"
    is_active = watch["is_active"]
    analysis = analysis_map.get(watch_id, {})

    # Build expander title with key info
    current_rate = analysis.get("current_rate", 0)
    rate_str = f"{current_rate:.4f}" if current_rate else "—"

    # Recommendation badge for title
    if analysis:
        should_alert = analysis.get("should_alert", False)
        recommendation = analysis.get("recommendation", "")
        if should_alert:
            badge = f"🟢 {recommendation}"
        else:
            badge = f"⚪ {recommendation}"
    else:
        badge = t("fx_watch.analysis.waiting")

    status_icon = "🟢" if is_active else "🔴"
    expander_title = f"{status_icon} 💱 {pair} — {rate_str} — {badge}"

    # Collapsible card
    with st.expander(expander_title, expanded=False):
        # Quick action row at top
        action_cols = st.columns([1, 1, 1, 3])

        with action_cols[0]:
            toggle_label = t("fx_watch.card.disable") if is_active else t("fx_watch.card.enable")
            if st.button(
                toggle_label,
                key=f"toggle_{watch_id}",
                use_container_width=True,
                help=t("fx_watch.card.toggle_help")
            ):
                if toggle_fx_watch(watch_id, is_active):
                    invalidate_fx_watch_caches()
                    _refresh_ui()
                else:
                    st.error(t("fx_watch.card.toggle_error"))

        with action_cols[1]:
            edit_watch_popover(watch)

        with action_cols[2]:
            if st.button(t("fx_watch.card.delete"), key=f"delete_{watch_id}", use_container_width=True):
                if delete_fx_watch(watch_id):
                    invalidate_fx_watch_caches()
                    _refresh_ui()
                else:
                    st.error(t("fx_watch.card.delete_error"))

        st.divider()

        if not _is_privacy():
            body_cols = st.columns([3, 2])

            with body_cols[0]:
                _render_fx_chart(
                    watch["base_currency"],
                    watch["quote_currency"],
                    watch["recent_high_days"],
                    watch_id,
                )

            with body_cols[1]:
                if analysis:
                    reasoning = analysis.get("reasoning", "")
                    st.markdown(t("fx_watch.analysis.title"))
                    st.caption(reasoning)
                else:
                    st.caption(t("fx_watch.analysis.waiting"))

                st.divider()

                st.markdown(t("fx_watch.settings.title"))
                st.caption(t("fx_watch.settings.recent_high", days=watch['recent_high_days']))
                st.caption(t("fx_watch.settings.consecutive", days=watch['consecutive_increase_days']))
                st.caption(t("fx_watch.settings.interval", hours=watch['reminder_interval_hours']))

                high_icon = "✅" if watch["alert_on_recent_high"] else "❌"
                consec_icon = "✅" if watch["alert_on_consecutive_increase"] else "❌"
                st.caption(t("fx_watch.settings.high_alert", icon=high_icon))
                st.caption(t("fx_watch.settings.consec_alert", icon=consec_icon))

                last_alert = watch.get("last_alerted_at")
                if last_alert:
                    alert_time = datetime.fromisoformat(last_alert).strftime("%Y-%m-%d %H:%M")
                    st.caption(t("fx_watch.settings.last_alert_time", time=alert_time))
                else:
                    st.caption(t("fx_watch.settings.last_alert_none"))
        else:
            st.info(t("fx_watch.privacy_enabled"))

st.divider()
