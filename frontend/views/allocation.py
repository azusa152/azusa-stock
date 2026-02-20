"""
Folio — Asset Allocation Page (個人資產配置).
Holdings management, rebalancing, and Telegram settings.

Step rendering is delegated to components in views/components/:
  - target_allocation.py  (Step 1)
  - holdings_manager.py   (Step 2)
  - rebalance.py          (Step 3)
  - currency_exposure.py  (Step 4)
  - withdrawal.py         (Step 5)
  - stress_test.py        (Step 6)
"""

import json

import streamlit as st

from config import (
    CASH_CURRENCY_OPTIONS,
    DISPLAY_CURRENCY_OPTIONS,
    HOLDING_IMPORT_TEMPLATE,
    HOLDINGS_EXPORT_FILENAME,
    STOCK_CATEGORY_OPTIONS,
    STOCK_MARKET_PLACEHOLDERS,
    get_cash_account_type_options,
    get_category_labels,
    get_privacy_toggle_label,
    get_stock_market_options,
)
from i18n import t
from utils import (
    api_get_silent,
    api_post,
    api_put,
    build_radar_lookup,
    fetch_currency_exposure,
    fetch_holdings,
    fetch_preferences,
    fetch_profile,
    fetch_rebalance,
    fetch_stress_test,
    fetch_templates,
    invalidate_all_caches,
    invalidate_holding_caches,
    invalidate_stock_caches,
    is_privacy,
    mask_id,
    on_privacy_change as _on_privacy_change,
    post_digest,
    post_telegram_test,
    put_notification_preferences,
    put_telegram_settings,
    refresh_ui,
    show_toast,
)
from views.components.currency_exposure import render_currency_exposure
from views.components.holdings_manager import render_holdings
from views.components.rebalance import render_rebalance
from views.components.stress_test import render_stress_test
from views.components.target_allocation import render_target
from views.components.withdrawal import render_withdrawal


# ---------------------------------------------------------------------------
# Session State Flag Handling (must run before any rendering)
# ---------------------------------------------------------------------------

if st.session_state.pop("holding_added", False):
    invalidate_holding_caches()
    invalidate_stock_caches()
    refresh_ui()


# ---------------------------------------------------------------------------
# Helpers (sidebar-only)
# ---------------------------------------------------------------------------

def _get_market_keys() -> list[str]:
    return list(get_stock_market_options().keys())


def _market_label(key: str) -> str:
    return get_stock_market_options()[key]["label"]


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------

_title_cols = st.columns([5, 1, 1])
with _title_cols[0]:
    st.title(t("allocation.title"))
    st.caption(t("allocation.caption"))
with _title_cols[1]:
    st.toggle(get_privacy_toggle_label(), key="privacy_mode", on_change=_on_privacy_change)
with _title_cols[2]:
    if st.button(t("common.refresh"), use_container_width=True):
        invalidate_all_caches()
        refresh_ui()


# ---------------------------------------------------------------------------
# SOP Manual
# ---------------------------------------------------------------------------

with st.expander(t("allocation.sop.title"), expanded=False):
    st.markdown(t("allocation.sop.content"))


# ---------------------------------------------------------------------------
# Sidebar: 新增持倉 + 匯出 / 匯入
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header(t("allocation.sidebar.header"))
    st.subheader(t("allocation.sidebar.add_holding"))

    asset_type = st.radio(
        t("allocation.sidebar.asset_type"),
        [t("allocation.sidebar.asset_stock"), t("allocation.sidebar.asset_bond"), t("allocation.sidebar.asset_cash")],
        horizontal=True,
        key="sidebar_asset_type",
    )

    # ---- Stock holding form ----
    if asset_type == t("allocation.sidebar.asset_stock"):
        sb_market = st.selectbox(
            t("allocation.sidebar.market"),
            options=_get_market_keys(),
            format_func=_market_label,
            key="sb_stock_market",
        )
        market_info = get_stock_market_options()[sb_market]
        st.caption(t("allocation.sidebar.currency", currency=market_info['currency']))

        # Ticker outside form for reactive radar lookup
        sb_ticker = st.text_input(
            t("allocation.sidebar.stock_ticker"),
            placeholder=STOCK_MARKET_PLACEHOLDERS.get(sb_market, "AAPL"),
            key="sb_stock_ticker",
        )

        # Radar auto-category lookup
        radar_lookup = build_radar_lookup()
        full_ticker_preview = (
            (sb_ticker.strip().upper() + market_info["suffix"])
            if sb_ticker.strip()
            else ""
        )
        is_in_radar = full_ticker_preview in radar_lookup
        radar_cat = radar_lookup.get(full_ticker_preview)

        if sb_ticker.strip():
            if is_in_radar:
                st.info(
                    t("allocation.sidebar.in_radar", category=get_category_labels().get(radar_cat, radar_cat))
                )
            else:
                st.caption(t("allocation.sidebar.not_in_radar"))

        # Compute default category index
        default_cat_idx = 0
        if is_in_radar and radar_cat in STOCK_CATEGORY_OPTIONS:
            default_cat_idx = STOCK_CATEGORY_OPTIONS.index(radar_cat)

        # Optional thesis (only for new stocks)
        sb_thesis = ""
        if sb_ticker.strip() and not is_in_radar:
            sb_thesis = st.text_area(
                t("allocation.sidebar.thesis_optional"),
                placeholder=t("allocation.sidebar.thesis_placeholder"),
                key="sb_stock_thesis",
            )

        with st.form("sidebar_stock_form", clear_on_submit=True):
            sb_cat = st.selectbox(
                t("allocation.sidebar.category"),
                options=STOCK_CATEGORY_OPTIONS,
                format_func=lambda x: get_category_labels().get(x, x),
                index=default_cat_idx,
                disabled=is_in_radar,
            )
            sb_qty = st.number_input(
                t("allocation.sidebar.quantity"), min_value=0.0, step=1.0, value=0.0
            )
            sb_cost = st.number_input(
                t("allocation.sidebar.avg_cost"), min_value=0.0, step=0.01, value=0.0
            )
            sb_broker = st.text_input(
                t("allocation.sidebar.broker_optional"),
                placeholder=t("allocation.sidebar.broker_placeholder"),
                key="sb_stock_broker",
            )

            if st.form_submit_button(t("allocation.sidebar.add_button")):
                if not sb_ticker.strip():
                    st.warning(t("allocation.sidebar.error_ticker"))
                elif sb_qty <= 0:
                    st.warning(t("allocation.sidebar.error_quantity"))
                else:
                    full_ticker = (
                        sb_ticker.strip().upper() + market_info["suffix"]
                    )
                    # Use radar category if stock already tracked
                    final_cat = radar_cat if is_in_radar else sb_cat
                    result = api_post(
                        "/holdings",
                        {
                            "ticker": full_ticker,
                            "category": final_cat,
                            "quantity": sb_qty,
                            "cost_basis": (
                                sb_cost if sb_cost > 0 else None
                            ),
                            "broker": (
                                sb_broker.strip() if sb_broker.strip() else None
                            ),
                            "currency": market_info["currency"],
                            "is_cash": False,
                        },
                    )
                    if result:
                        st.success(t("allocation.sidebar.added", ticker=full_ticker))
                        # Auto-add to radar if not tracked yet
                        if not is_in_radar:
                            radar_result = api_post(
                                "/ticker",
                                {
                                    "ticker": full_ticker,
                                    "category": final_cat,
                                    "thesis": sb_thesis.strip()
                                    or "Added via holdings",
                                    "tags": [],
                                },
                            )
                            if radar_result:
                                st.info(t("allocation.sidebar.auto_radar"))
                                invalidate_stock_caches()
                        st.session_state["holding_added"] = True

    # ---- Bond holding form ----
    elif asset_type == t("allocation.sidebar.asset_bond"):
        # Ticker outside form for reactive radar lookup
        sb_bond_ticker = st.text_input(
            t("allocation.sidebar.bond_ticker"),
            placeholder="TLT, BND, SGOV",
            key="sb_bond_ticker",
        )

        # Radar auto-category lookup
        radar_lookup_b = build_radar_lookup()
        bond_ticker_preview = (
            sb_bond_ticker.strip().upper() if sb_bond_ticker.strip() else ""
        )
        bond_in_radar = bond_ticker_preview in radar_lookup_b

        if sb_bond_ticker.strip():
            if bond_in_radar:
                st.info(t("allocation.sidebar.bond_in_radar"))
            else:
                st.caption(t("allocation.sidebar.not_in_radar"))

        # Optional thesis (only for new bonds)
        sb_bond_thesis = ""
        if sb_bond_ticker.strip() and not bond_in_radar:
            sb_bond_thesis = st.text_area(
                t("allocation.sidebar.thesis_optional"),
                placeholder=t("allocation.sidebar.thesis_placeholder"),
                key="sb_bond_thesis",
            )

        with st.form("sidebar_bond_form", clear_on_submit=True):
            sb_bond_currency = st.selectbox(
                t("allocation.sidebar.currency_label"), options=CASH_CURRENCY_OPTIONS
            )
            sb_bond_qty = st.number_input(
                t("allocation.sidebar.quantity"), min_value=0.0, step=1.0, value=0.0, key="sb_bqty"
            )
            sb_bond_cost = st.number_input(
                t("allocation.sidebar.avg_cost"),
                min_value=0.0,
                step=0.01,
                value=0.0,
                key="sb_bcost",
            )
            sb_bond_broker = st.text_input(
                t("allocation.sidebar.broker_optional"),
                placeholder=t("allocation.sidebar.broker_placeholder"),
                key="sb_bond_broker",
            )

            if st.form_submit_button(t("allocation.sidebar.add_button")):
                if not sb_bond_ticker.strip():
                    st.warning(t("allocation.sidebar.error_bond_ticker"))
                elif sb_bond_qty <= 0:
                    st.warning(t("allocation.sidebar.error_quantity"))
                else:
                    bond_full = sb_bond_ticker.strip().upper()
                    result = api_post(
                        "/holdings",
                        {
                            "ticker": bond_full,
                            "category": "Bond",
                            "quantity": sb_bond_qty,
                            "cost_basis": (
                                sb_bond_cost if sb_bond_cost > 0 else None
                            ),
                            "broker": (
                                sb_bond_broker.strip()
                                if sb_bond_broker.strip()
                                else None
                            ),
                            "currency": sb_bond_currency,
                            "is_cash": False,
                        },
                    )
                    if result:
                        st.success(t("allocation.sidebar.added", ticker=bond_full))
                        # Auto-add to radar if not tracked yet
                        if not bond_in_radar:
                            radar_result = api_post(
                                "/ticker",
                                {
                                    "ticker": bond_full,
                                    "category": "Bond",
                                    "thesis": sb_bond_thesis.strip()
                                    or "Added via holdings",
                                    "tags": [],
                                },
                            )
                            if radar_result:
                                st.info(t("allocation.sidebar.auto_radar"))
                                invalidate_stock_caches()
                        st.session_state["holding_added"] = True

    # ---- Cash holding form ----
    else:
        with st.form("sidebar_cash_form", clear_on_submit=True):
            cash_currency = st.selectbox(
                t("allocation.sidebar.currency_label"), options=CASH_CURRENCY_OPTIONS
            )
            cash_amount = st.number_input(
                t("allocation.sidebar.cash_amount"), min_value=0.0, step=100.0, value=0.0
            )
            cash_bank = st.text_input(
                t("allocation.sidebar.cash_bank"),
                placeholder=t("allocation.sidebar.cash_bank_placeholder"),
            )
            cash_account_type = st.selectbox(
                t("allocation.sidebar.cash_account_type"),
                options=[t("allocation.sidebar.not_specified")] + get_cash_account_type_options(),
            )
            cash_notes = st.text_area(
                t("allocation.sidebar.cash_notes"),
                placeholder=t("allocation.sidebar.cash_notes_placeholder"),
            )

            if st.form_submit_button(t("allocation.sidebar.add_button")):
                if cash_amount <= 0:
                    st.warning(t("allocation.sidebar.error_cash_amount"))
                else:
                    result = api_post(
                        "/holdings/cash",
                        {
                            "currency": cash_currency,
                            "amount": cash_amount,
                            "broker": (
                                cash_bank.strip()
                                if cash_bank.strip()
                                else None
                            ),
                            "account_type": (
                                cash_account_type
                                if cash_account_type != t("allocation.sidebar.not_specified")
                                else None
                            ),
                        },
                    )
                    if result:
                        label_parts = [cash_currency]
                        if cash_bank.strip():
                            label_parts.append(cash_bank.strip())
                        st.success(
                            t("allocation.sidebar.cash_added", label=' - '.join(label_parts), amount=f"{cash_amount:,.0f}")
                        )
                        st.session_state["holding_added"] = True

    st.divider()

    # -- Export Holdings --
    st.subheader(t("allocation.sidebar.export_title"))
    export_h = api_get_silent("/holdings/export")
    if export_h:
        st.download_button(
            t("allocation.sidebar.download_json"),
            data=json.dumps(export_h, ensure_ascii=False, indent=2),
            file_name=HOLDINGS_EXPORT_FILENAME,
            mime="application/json",
            use_container_width=True,
        )
        st.caption(t("allocation.sidebar.export_count", count=len(export_h)))
    else:
        st.caption(t("allocation.sidebar.no_export"))

    st.divider()

    # -- Import Holdings --
    st.subheader(t("allocation.sidebar.import_title"))
    h_file = st.file_uploader(
        t("allocation.sidebar.upload_json"),
        type=["json"],
        key="import_holdings_file",
        label_visibility="collapsed",
    )
    if h_file is not None:
        try:
            h_data = json.loads(h_file.getvalue().decode("utf-8"))
            if isinstance(h_data, list):
                st.caption(t("allocation.sidebar.import_detected", count=len(h_data)))
                if st.button(t("allocation.sidebar.import_confirm"), use_container_width=True):
                    result = api_post("/holdings/import", h_data)
                    if result:
                        st.success(
                            result.get("message", t("allocation.sidebar.import_success"))
                        )
                        invalidate_holding_caches()
                        st.rerun()
            else:
                st.warning(t("allocation.sidebar.import_error_format"))
        except json.JSONDecodeError:
            st.error(t("allocation.sidebar.import_error_json"))

    st.download_button(
        t("allocation.sidebar.download_template"),
        data=HOLDING_IMPORT_TEMPLATE,
        file_name="holding_import_template.json",
        mime="application/json",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Shared data (fetched once, available to all tabs)
# ---------------------------------------------------------------------------

try:
    _templates = fetch_templates() or []
    _profile = fetch_profile()
    _holdings = fetch_holdings() or []
except Exception as e:
    st.error(t("allocation.error_loading", error=e))
    _templates, _profile, _holdings = [], None, []

_setup_done = bool(_profile and _holdings)
_SETUP_MSG = t("allocation.setup_required")


# ---------------------------------------------------------------------------
# Main Content: 4 narrative-driven tabs (P4)
# Portfolio | Risk | Actions | Settings
# ---------------------------------------------------------------------------

tab_portfolio, tab_risk, tab_actions, tab_settings = st.tabs([
    t("allocation.tab.portfolio"),
    t("allocation.tab.risk"),
    t("allocation.tab.actions"),
    t("allocation.tab.settings"),
])


# ===========================================================================
# Tab 1: Portfolio — Display Currency + Rebalance Analysis
# (Health Score, Pies/Treemap, Drift with $, Holdings, X-Ray, Sector)
# ===========================================================================

with tab_portfolio:
    if _setup_done:
        try:
            # Display currency selector lives here so it's visible alongside analysis
            _ctrl_cols = st.columns([3, 1])
            with _ctrl_cols[0]:
                display_cur = st.selectbox(
                    t("allocation.display_currency"),
                    options=DISPLAY_CURRENCY_OPTIONS,
                    index=DISPLAY_CURRENCY_OPTIONS.index("USD"),
                    key="display_currency",
                )
            with _ctrl_cols[1]:
                st.write("")  # vertical spacer
                if st.button(
                    t("allocation.refresh_button"),
                    type="secondary",
                    key="btn_refresh_analysis",
                ):
                    fetch_rebalance.clear()
                    fetch_stress_test.clear()
                    fetch_currency_exposure.clear()
                    st.rerun()
        except Exception as e:
            st.error(t("allocation.error_setup", error=e))
            display_cur = "USD"

        render_rebalance(_profile, _holdings, st.session_state.get("display_currency", "USD"))
    else:
        st.info(_SETUP_MSG)

# Resolved for Risk / Actions tabs (display currency selectbox already rendered above)
_display_cur = st.session_state.get("display_currency", "USD")


# ===========================================================================
# Tab 2: Risk — FX Exposure + Stress Test
# ===========================================================================

with tab_risk:
    if _setup_done:
        st.subheader(t("allocation.tab.fx"))
        render_currency_exposure(_profile, _holdings, _display_cur)

        st.divider()
        st.subheader(t("allocation.tab.stress"))
        render_stress_test(display_currency=_display_cur)
    else:
        st.info(_SETUP_MSG)


# ===========================================================================
# Tab 3: Actions — Smart Withdrawal
# ===========================================================================

with tab_actions:
    if _setup_done:
        render_withdrawal(_profile, _holdings)
    else:
        st.info(_SETUP_MSG)


# ===========================================================================
# Tab 4: Settings — Target Allocation + Holdings + Telegram
# ===========================================================================

with tab_settings:
    try:
        # Step 1 — collapsible when profile exists
        with st.expander(
            t("allocation.step1_title"),
            expanded=not _profile,
        ):
            render_target(_templates, _profile, _holdings)

        # Step 2 — always visible
        st.subheader(t("allocation.step2_title"))
        render_holdings(_holdings)

    except Exception as e:
        st.error(t("allocation.error_setup", error=e))

    st.divider()
    st.subheader(t("allocation.telegram.title"))
    st.caption(t("allocation.telegram.caption"))

    tg_settings = api_get_silent("/settings/telegram")

    if tg_settings:
        mode_label = (
            t("allocation.telegram.mode_custom")
            if tg_settings.get("use_custom_bot")
            else t("allocation.telegram.mode_default")
        )
        tg_cols = st.columns(3)
        with tg_cols[0]:
            st.metric(t("allocation.telegram.mode"), mode_label)
        with tg_cols[1]:
            # Mask Chat ID in privacy mode
            chat_id = tg_settings.get("telegram_chat_id") or t("allocation.telegram.not_set")
            if chat_id != t("allocation.telegram.not_set"):
                chat_id = mask_id(chat_id)
            st.metric(t("allocation.telegram.chat_id"), chat_id)
        with tg_cols[2]:
            st.metric(
                t("allocation.telegram.custom_token"),
                tg_settings.get("custom_bot_token_masked") or t("allocation.telegram.not_set"),
            )

    with st.expander(
        t("allocation.telegram.edit_title"),
        expanded=not bool(
            tg_settings and tg_settings.get("telegram_chat_id")
        ),
    ):
        with st.form("telegram_settings_form"):
            # Don't pre-fill Chat ID in privacy mode to prevent shoulder surfing
            tg_chat_value = (tg_settings or {}).get("telegram_chat_id", "")
            if is_privacy() and tg_chat_value:
                tg_chat_value = ""
            tg_chat = st.text_input(
                t("allocation.telegram.chat_id_input"),
                value=tg_chat_value,
                placeholder=t("allocation.telegram.chat_id_placeholder"),
            )
            tg_token = st.text_input(
                t("allocation.telegram.token_input"),
                value="",
                placeholder=t("allocation.telegram.token_placeholder"),
                type="password",
            )
            tg_custom = st.toggle(
                t("allocation.telegram.use_custom"),
                value=(tg_settings or {}).get("use_custom_bot", False),
            )
            st.caption(t("allocation.telegram.hint"))

            if st.form_submit_button(t("allocation.telegram.save_button")):
                payload: dict = {
                    "telegram_chat_id": tg_chat.strip(),
                    "use_custom_bot": tg_custom,
                }
                if tg_token.strip():
                    payload["custom_bot_token"] = tg_token.strip()
                level, msg = put_telegram_settings(payload)
                show_toast(level, msg)
                if level == "success":
                    st.rerun()

    # Action buttons (outside form)
    if tg_settings and tg_settings.get("telegram_chat_id"):
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button(t("allocation.telegram.test_button"), key="test_telegram_btn"):
                level, msg = post_telegram_test()
                show_toast(level, msg)
        with btn_cols[1]:
            if st.button(t("allocation.telegram.digest_button"), key="trigger_digest_btn"):
                level, msg = post_digest()
                show_toast(level, msg)

    # -------------------------------------------------------------------
    # Notification Preferences — selective alert toggles
    # -------------------------------------------------------------------
    st.divider()
    st.subheader(t("allocation.telegram.notif_title"))
    st.caption(t("allocation.telegram.notif_caption"))

    _NOTIF_LABELS: dict[str, tuple[str, str]] = {
        "scan_alerts": (t("allocation.telegram.notif.scan_alerts"), t("allocation.telegram.notif.scan_alerts_help")),
        "price_alerts": (t("allocation.telegram.notif.price_alerts"), t("allocation.telegram.notif.price_alerts_help")),
        "weekly_digest": (t("allocation.telegram.notif.weekly_digest"), t("allocation.telegram.notif.weekly_digest_help")),
        "xray_alerts": (t("allocation.telegram.notif.xray_alerts"), t("allocation.telegram.notif.xray_alerts_help")),
        "fx_alerts": (t("allocation.telegram.notif.fx_alerts"), t("allocation.telegram.notif.fx_alerts_help")),
    }

    prefs_resp = api_get_silent("/settings/preferences")
    current_notif_prefs = (prefs_resp or {}).get(
        "notification_preferences",
        {k: True for k in _NOTIF_LABELS},
    )
    current_privacy = (prefs_resp or {}).get("privacy_mode", False)

    with st.form("notification_preferences_form"):
        new_prefs: dict[str, bool] = {}
        for key, (label, help_text) in _NOTIF_LABELS.items():
            new_prefs[key] = st.checkbox(
                label,
                value=current_notif_prefs.get(key, True),
                help=help_text,
                key=f"notif_pref_{key}",
            )

        if st.form_submit_button(t("allocation.telegram.save_notif")):
            level, msg = put_notification_preferences(current_privacy, new_prefs)
            show_toast(level, msg)
            if level == "success":
                fetch_preferences.clear()
                st.rerun()
