"""
Folio — Radar Page (投資雷達).
Stock tracking, thesis versioning, scanning, and market signals.
"""

import json

import streamlit as st

from config import (
    CASH_CURRENCY_OPTIONS,
    CATEGORY_OPTIONS,
    DEFAULT_TAG_OPTIONS,
    EXPORT_FILENAME,
    RADAR_CATEGORY_OPTIONS,
    STOCK_CATEGORY_OPTIONS,
    STOCK_IMPORT_TEMPLATE,
    STOCK_MARKET_PLACEHOLDERS,
    get_category_labels,
    get_stock_market_options,
)
from i18n import t
from utils import (
    api_get,
    api_get_silent,
    api_post,
    fetch_enriched_stocks,
    fetch_last_scan,
    fetch_removed_stocks,
    fetch_resonance_overview,
    fetch_scan_status,
    fetch_stocks,
    fetch_thesis_history,
    format_utc_timestamp,
    invalidate_all_caches,
    invalidate_stock_caches,
    refresh_ui,
    render_reorder_section,
    render_stock_card,
    render_thesis_history,
    trigger_scan,
)


# ---------------------------------------------------------------------------
# Session State Flag Handling (must run before any rendering)
# ---------------------------------------------------------------------------

if st.session_state.pop("stock_added", False):
    invalidate_stock_caches()
    refresh_ui()


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------

_title_col, _refresh_col = st.columns([6, 1])
with _title_col:
    st.title(t("radar.title"))
    st.caption(t("radar.caption"))
with _refresh_col:
    if st.button(t("common.refresh"), use_container_width=True):
        invalidate_all_caches()
        refresh_ui()

with st.expander(t("radar.sop.title"), expanded=False):
    st.markdown(t("radar.sop.content"))


# ---------------------------------------------------------------------------
# Sidebar: 操作面板 (Radar-specific)
# ---------------------------------------------------------------------------

def _get_market_keys() -> list[str]:
    return list(get_stock_market_options().keys())


def _market_label(key: str) -> str:
    return get_stock_market_options()[key]["label"]


with st.sidebar:
    st.header(t("radar.panel_header"))

    # -- Add Stock / Bond --
    st.subheader(t("radar.panel.add_stock"))

    radar_asset_type = st.radio(
        t("radar.form.asset_type"),
        [t("radar.form.asset_stock"), t("radar.form.asset_bond")],
        horizontal=True,
        key="radar_asset_type",
    )

    if radar_asset_type == t("radar.form.asset_stock"):
        radar_market = st.selectbox(
            t("radar.form.market"),
            options=_get_market_keys(),
            format_func=_market_label,
            key="radar_stock_market",
        )
        radar_market_info = get_stock_market_options()[radar_market]
        st.caption(t("radar.form.currency", currency=radar_market_info['currency']))

        with st.form("add_stock_form", clear_on_submit=True):
            new_ticker = st.text_input(
                t("radar.form.ticker"),
                placeholder=STOCK_MARKET_PLACEHOLDERS.get(
                    radar_market, "AAPL"
                ),
            )
            new_category = st.selectbox(
                t("radar.form.category"),
                options=STOCK_CATEGORY_OPTIONS,
                format_func=lambda x: get_category_labels().get(x, x),
            )
            new_thesis = st.text_area(
                t("radar.form.thesis"), placeholder=t("radar.form.thesis_placeholder")
            )
            new_tags = st.multiselect(
                t("radar.form.tags"),
                options=DEFAULT_TAG_OPTIONS,
            )
            submitted = st.form_submit_button(t("radar.form.add_button"))

            if submitted:
                if not new_ticker.strip():
                    st.warning(t("radar.form.error_no_ticker"))
                elif not new_thesis.strip():
                    st.warning(t("radar.form.error_no_thesis"))
                else:
                    full_ticker = (
                        new_ticker.strip().upper()
                        + radar_market_info["suffix"]
                    )
                    tags = list(new_tags)
                    tags.append(radar_market_info["label"])
                    tags.append(radar_market_info["currency"])
                    result = api_post(
                        "/ticker",
                        {
                            "ticker": full_ticker,
                            "category": new_category,
                            "thesis": new_thesis.strip(),
                            "tags": tags,
                        },
                    )
                    if result:
                        st.success(t("radar.form.success_added", ticker=full_ticker))
                        st.session_state["stock_added"] = True

    else:  # Bond mode
        with st.form("add_bond_form", clear_on_submit=True):
            bond_ticker = st.text_input(
                t("radar.form.bond_ticker"), placeholder="TLT, BND, SGOV"
            )
            bond_currency = st.selectbox(
                t("radar.form.currency"), options=CASH_CURRENCY_OPTIONS
            )
            bond_thesis = st.text_area(
                t("radar.form.thesis"), placeholder=t("radar.form.bond_thesis_placeholder")
            )
            bond_tags = st.multiselect(
                t("radar.form.tags"),
                options=DEFAULT_TAG_OPTIONS,
                key="bond_tags",
            )
            bond_submitted = st.form_submit_button(t("radar.form.add_button"))

            if bond_submitted:
                if not bond_ticker.strip():
                    st.warning(t("radar.form.error_no_bond_ticker"))
                elif not bond_thesis.strip():
                    st.warning(t("radar.form.error_no_thesis"))
                else:
                    tags = list(bond_tags)
                    tags.append(bond_currency)
                    result = api_post(
                        "/ticker",
                        {
                            "ticker": bond_ticker.strip().upper(),
                            "category": "Bond",
                            "thesis": bond_thesis.strip(),
                            "tags": tags,
                        },
                    )
                    if result:
                        st.success(
                            t("radar.form.success_added", ticker=bond_ticker.strip().upper())
                        )
                        st.session_state["stock_added"] = True

    st.divider()

    # -- Scan --
    st.subheader(t("radar.panel.scan"))
    st.caption(t("radar.scan.caption"))

    _scan_initiated = st.session_state.get("scan_initiated", False)
    _is_backend_running = fetch_scan_status()

    # Clear stale session flag once backend confirms the scan has finished.
    if _scan_initiated and not _is_backend_running:
        st.session_state.pop("scan_initiated", None)
        _scan_initiated = False

    _scan_running = _is_backend_running or _scan_initiated

    if _scan_running:
        st.info(t("radar.scan.running"))
        st.caption(t("radar.scan.running_description"))

    if st.button(
        t("radar.scan.button"),
        use_container_width=True,
        disabled=_scan_running,
    ):
        with st.spinner(t("radar.scan.running")):
            result = trigger_scan()
        if result:
            if result.get("error_code") == "scan_in_progress":
                st.warning(t("radar.scan.already_running"))
            else:
                st.session_state["scan_initiated"] = True
                st.success(t("radar.scan.success", message=result.get("message", t("radar.scan.default_success"))))
                st.rerun()
        else:
            st.session_state.pop("scan_initiated", None)

    st.divider()

    # -- Export Watchlist --
    st.subheader(t("radar.panel.export"))
    export_data = api_get_silent("/stocks/export")
    if export_data:
        export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label=t("radar.export.download_button"),
            data=export_json,
            file_name=EXPORT_FILENAME,
            mime="application/json",
            use_container_width=True,
        )
        st.caption(t("radar.export.count", count=len(export_data)))
    else:
        st.caption(t("radar.export.no_stocks"))

    st.divider()

    # -- Import Watchlist --
    st.subheader(t("radar.panel.import"))
    uploaded_file = st.file_uploader(
        t("radar.import.file_label"),
        type=["json"],
        key="import_file",
        label_visibility="collapsed",
    )
    if uploaded_file is not None:
        try:
            import_data = json.loads(uploaded_file.getvalue().decode("utf-8"))
            if isinstance(import_data, list):
                st.caption(t("radar.import.detected", count=len(import_data)))
                if st.button(t("radar.import.confirm_button"), use_container_width=True):
                    result = api_post("/stocks/import", import_data)
                    if result:
                        st.success(result.get("message", t("radar.import.success")))
                        if result.get("errors"):
                            for err in result["errors"]:
                                st.warning(f"⚠️ {err}")
                        invalidate_stock_caches()
                        refresh_ui()
            else:
                st.warning(t("radar.import.error_not_array"))
        except json.JSONDecodeError:
            st.error(t("radar.import.error_json"))

    st.download_button(
        t("radar.import.template_button"),
        data=STOCK_IMPORT_TEMPLATE,
        file_name="stock_import_template.json",
        mime="application/json",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Main Dashboard: Stock Tabs
# ---------------------------------------------------------------------------

_load_placeholder = st.empty()
stocks_data = fetch_stocks()
removed_data = fetch_removed_stocks()

if stocks_data is None:
    _load_placeholder.empty()
    st.error(t("radar.loading.error"))
    st.caption(t("radar.loading.error_hint"))
    if st.button(t("radar.loading.retry_button"), type="primary"):
        invalidate_all_caches()
        st.rerun()
    st.stop()

_load_placeholder.success(t("radar.loading.success", count=len(stocks_data)))

# Data freshness indicator
_last_scan = fetch_last_scan()
if _last_scan and _last_scan.get("last_scanned_at"):
    _browser_tz = st.session_state.get("browser_tz")
    _scan_time = format_utc_timestamp(_last_scan["last_scanned_at"], _browser_tz)
    st.caption(t("radar.last_scan_time", time=_scan_time))
else:
    st.caption(t("radar.no_scan_yet"))

# Group stocks by category (radar categories only)
category_map = {cat: [] for cat in RADAR_CATEGORY_OPTIONS}
for stock in stocks_data or []:
    cat = stock.get("category", "Growth")
    if cat in category_map:
        category_map[cat].append(stock)

removed_list = removed_data or []

# Batch-fetch enriched data (signals, earnings, dividends) in a single API call
# to avoid N+1 individual requests when rendering stock cards.
_enriched_list = fetch_enriched_stocks() or []
_enriched_map: dict[str, dict] = {e["ticker"]: e for e in _enriched_list if "ticker" in e}

# Fetch resonance data for all tickers in a single GET /resonance call
# (cached 24 h). Falls back to empty dict so cards still render on error.
_resonance_map: dict[str, list] = fetch_resonance_overview() or {}

# Build tab labels
tab_labels = [
    t("radar.tab.trend_setter", count=len(category_map['Trend_Setter'])),
    t("radar.tab.moat", count=len(category_map['Moat'])),
    t("radar.tab.growth", count=len(category_map['Growth'])),
    t("radar.tab.bond", count=len(category_map['Bond'])),
    t("radar.tab.removed", count=len(removed_list)),
]

tab_trend, tab_moat, tab_growth, tab_bond, tab_archive = st.tabs(tab_labels)

# Render stock category tabs
_category_tabs = [tab_trend, tab_moat, tab_growth, tab_bond]
for _cat, _tab in zip(RADAR_CATEGORY_OPTIONS, _category_tabs):
    with _tab:
        _stocks = category_map[_cat]
        if _stocks:
            render_reorder_section(_cat, _stocks)
            for stock in _stocks:
                render_stock_card(
                    stock,
                    enrichment=_enriched_map.get(stock["ticker"]),
                    resonance=_resonance_map.get(stock["ticker"]),
                )
        else:
            st.info(
                t("radar.empty_category", category=get_category_labels()[_cat])
            )

# Archive tab
with tab_archive:
    if removed_list:
        for removed in removed_list:
            ticker = removed["ticker"]
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.subheader(f"📦 {ticker}")
                    category_label = get_category_labels().get(
                        removed.get("category", ""),
                        removed.get("category", ""),
                    )
                    st.caption(t("radar.removed.category", category=category_label))
                    removed_at = removed.get("removed_at", "")
                    st.caption(
                        t("radar.removed.date", date=removed_at[:10] if removed_at else t("radar.removed.unknown"))
                    )

                with col2:
                    st.markdown(t("radar.removed.reason_title"))
                    st.error(removed.get("removal_reason", t("radar.removed.unknown")))

                    st.markdown(t("radar.removed.last_thesis_title"))
                    st.info(removed.get("current_thesis", t("radar.removed.no_thesis")))

                    # -- Removal History --
                    with st.expander(
                        t("radar.removed.history_title", ticker=ticker), expanded=False
                    ):
                        removals = api_get(f"/ticker/{ticker}/removals")
                        if removals:
                            for entry in removals:
                                created = entry.get("created_at", "")
                                st.markdown(
                                    f"**{created[:10] if created else t('radar.removed.unknown_date')}**"
                                )
                                st.text(entry.get("reason", ""))
                                st.divider()
                        else:
                            st.caption(t("radar.removed.no_history"))

                    # -- Thesis History --
                    with st.expander(
                        t("radar.removed.thesis_history_title", ticker=ticker), expanded=False
                    ):
                        history = fetch_thesis_history(ticker)
                        render_thesis_history(history or [])

                    # -- Reactivate --
                    with st.expander(
                        t("radar.removed.reactivate_title", ticker=ticker), expanded=False
                    ):
                        reactivate_cat = st.selectbox(
                            t("radar.removed.reactivate_category"),
                            options=CATEGORY_OPTIONS,
                            format_func=lambda x: get_category_labels().get(x, x),
                            key=f"reactivate_cat_{ticker}",
                        )
                        reactivate_thesis = st.text_area(
                            t("radar.removed.reactivate_thesis"),
                            key=f"reactivate_thesis_{ticker}",
                            placeholder=t("radar.removed.reactivate_thesis_placeholder"),
                        )
                        if st.button(
                            t("radar.removed.reactivate_button"),
                            key=f"reactivate_btn_{ticker}",
                            type="primary",
                        ):
                            payload = {"category": reactivate_cat}
                            if reactivate_thesis.strip():
                                payload["thesis"] = reactivate_thesis.strip()
                            result = api_post(
                                f"/ticker/{ticker}/reactivate", payload
                            )
                            if result:
                                st.success(
                                    result.get("message", t("radar.removed.reactivate_success"))
                                )
                                invalidate_stock_caches()
                                refresh_ui()
    else:
        st.info(t("radar.removed.no_removed_stocks"))
