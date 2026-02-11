"""
Folio — Shared utilities for the Streamlit frontend.
API helpers, cached data fetchers, and reusable UI rendering functions.
"""

from datetime import datetime as dt
from datetime import timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_sortables import sort_items

from config import (
    API_DELETE_TIMEOUT,
    API_DIVIDEND_TIMEOUT,
    API_GET_ENRICHED_TIMEOUT,
    API_EARNINGS_TIMEOUT,
    API_FEAR_GREED_TIMEOUT,
    API_GET_TIMEOUT,
    API_PATCH_TIMEOUT,
    API_POST_TIMEOUT,
    API_PRICE_HISTORY_TIMEOUT,
    API_PUT_TIMEOUT,
    API_REBALANCE_TIMEOUT,
    API_SIGNALS_TIMEOUT,
    BACKEND_URL,
    BIAS_OVERHEATED_UI,
    BIAS_OVERSOLD_UI,
    CACHE_TTL_ALERTS,
    CACHE_TTL_DIVIDEND,
    CACHE_TTL_EARNINGS,
    CACHE_TTL_HOLDINGS,
    CACHE_TTL_LAST_SCAN,
    CACHE_TTL_MOAT,
    CACHE_TTL_PREFERENCES,
    CACHE_TTL_PRICE_HISTORY,
    CACHE_TTL_PROFILE,
    CACHE_TTL_REMOVED,
    CACHE_TTL_REBALANCE,
    CACHE_TTL_SCAN_HISTORY,
    CACHE_TTL_SIGNALS,
    CACHE_TTL_FEAR_GREED,
    CACHE_TTL_STOCKS,
    CACHE_TTL_TEMPLATES,
    CACHE_TTL_THESIS,
    CATEGORY_LABELS,
    CATEGORY_OPTIONS,
    DEFAULT_ALERT_THRESHOLD,
    DEFAULT_TAG_OPTIONS,
    EARNINGS_BADGE_DAYS_THRESHOLD,
    MARGIN_BAD_CHANGE_THRESHOLD,
    PRICE_CHART_DEFAULT_PERIOD,
    PRICE_CHART_HEIGHT,
    PRICE_CHART_PERIODS,
    PRICE_WEAK_BIAS_THRESHOLD,
    REORDER_MIN_STOCKS,
    SCAN_HISTORY_CARD_LIMIT,
    SCAN_SIGNAL_ICONS,
    SKIP_MOAT_CATEGORIES,
    SKIP_SIGNALS_CATEGORIES,
    PRIVACY_MASK,
    TICKER_DEFAULT_MARKET,
    TICKER_SUFFIX_TO_MARKET,
    WHALEWISDOM_STOCK_URL,
)


# ---------------------------------------------------------------------------
# Core Helpers
# ---------------------------------------------------------------------------


def refresh_ui() -> None:
    """Rerun the page. Caller should clear specific caches first."""
    st.rerun()


# ---------------------------------------------------------------------------
# Targeted Cache Invalidation
# ---------------------------------------------------------------------------


def invalidate_stock_caches() -> None:
    """After adding/removing/updating stocks."""
    fetch_stocks.clear()
    fetch_enriched_stocks.clear()
    fetch_removed_stocks.clear()


def invalidate_holding_caches() -> None:
    """After adding/removing/editing holdings."""
    fetch_holdings.clear()
    fetch_rebalance.clear()
    fetch_currency_exposure.clear()


def invalidate_profile_caches() -> None:
    """After changing investment profile/config."""
    fetch_profile.clear()
    fetch_rebalance.clear()
    fetch_currency_exposure.clear()


def invalidate_all_caches() -> None:
    """Nuclear option — only for explicit refresh button."""
    st.cache_data.clear()


def format_utc_timestamp(iso_str: str, tz_name: str | None = None) -> str:
    """Convert UTC ISO timestamp to 'YYYY-MM-DD HH:MM:SS (TZ)' in user timezone."""
    try:
        utc_dt = dt.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        if tz_name:
            local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
            return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})"
        return f"{iso_str[:19].replace('T', ' ')} (UTC)"
    except Exception:
        return f"{iso_str[:19].replace('T', ' ')} (UTC)"


def infer_market_label(ticker: str) -> str:
    """Infer market label from ticker suffix (e.g. '.TW' -> '🇹🇼 台股')."""
    for suffix, label in TICKER_SUFFIX_TO_MARKET.items():
        if ticker.upper().endswith(suffix):
            return label
    return TICKER_DEFAULT_MARKET


# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------


def api_get(path: str) -> dict | list | None:
    """GET request to Backend API."""
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=API_GET_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_post(path: str, json_data: dict | list) -> dict | None:
    """POST request to Backend API."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}{path}", json=json_data, timeout=API_POST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_patch(path: str, json_data: dict) -> dict | None:
    """PATCH request to Backend API."""
    try:
        resp = requests.patch(
            f"{BACKEND_URL}{path}", json=json_data, timeout=API_PATCH_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_put(path: str, json_data: dict) -> dict | None:
    """PUT request to Backend API."""
    try:
        resp = requests.put(
            f"{BACKEND_URL}{path}", json=json_data, timeout=API_PUT_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_delete(path: str) -> dict | None:
    """DELETE request to Backend API."""
    try:
        resp = requests.delete(f"{BACKEND_URL}{path}", timeout=API_DELETE_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_get_silent(path: str, timeout: int | None = None) -> dict | list | None:
    """GET request to Backend API (silent mode — no error display)."""
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=timeout or API_GET_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# Cached Data Fetchers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_STOCKS, show_spinner="載入股票資料中...")
def fetch_stocks() -> list | None:
    """Fetch all tracked stocks (DB data only)."""
    return api_get("/stocks")


@st.cache_data(ttl=CACHE_TTL_STOCKS, show_spinner="載入豐富股票資料中...")
@st.cache_data(ttl=CACHE_TTL_STOCKS, show_spinner=False)
def fetch_enriched_stocks() -> list | None:
    """Fetch all active stocks with signals, earnings, and dividends in one batch.

    Uses a short dedicated timeout so the page loads fast even on cold cache.
    Returns None silently if the backend hasn't finished warming up yet.
    """
    return api_get_silent("/stocks/enriched", timeout=API_GET_ENRICHED_TIMEOUT)


def build_radar_lookup() -> dict[str, str]:
    """Return {TICKER: category} from cached radar stocks for quick lookups."""
    stocks = fetch_stocks()
    if not stocks:
        return {}
    return {s["ticker"].upper(): s["category"] for s in stocks if s.get("ticker")}


@st.cache_data(ttl=CACHE_TTL_SIGNALS, show_spinner=False)
def fetch_signals(ticker: str) -> dict | None:
    """Fetch technical signals for a single stock (yfinance)."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/ticker/{ticker}/signals", timeout=API_SIGNALS_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_REMOVED, show_spinner="載入已移除股票...")
def fetch_removed_stocks() -> list | None:
    """Fetch removed stocks list."""
    return api_get("/stocks/removed")


@st.cache_data(ttl=CACHE_TTL_EARNINGS, show_spinner=False)
def fetch_earnings(ticker: str) -> dict | None:
    """Fetch earnings date."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/ticker/{ticker}/earnings", timeout=API_EARNINGS_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_DIVIDEND, show_spinner=False)
def fetch_dividend(ticker: str) -> dict | None:
    """Fetch dividend info."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/ticker/{ticker}/dividend", timeout=API_DIVIDEND_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_MOAT, show_spinner=False)
def fetch_moat(ticker: str) -> dict | None:
    """Fetch moat analysis data."""
    return api_get(f"/ticker/{ticker}/moat")


@st.cache_data(ttl=CACHE_TTL_SCAN_HISTORY, show_spinner=False)
def fetch_scan_history(
    ticker: str, limit: int = SCAN_HISTORY_CARD_LIMIT
) -> list | None:
    """Fetch scan history."""
    return api_get(f"/ticker/{ticker}/scan-history?limit={limit}")


@st.cache_data(ttl=CACHE_TTL_ALERTS, show_spinner=False)
def fetch_alerts(ticker: str) -> list | None:
    """Fetch price alerts."""
    return api_get(f"/ticker/{ticker}/alerts")


@st.cache_data(ttl=CACHE_TTL_THESIS, show_spinner=False)
def fetch_thesis_history(ticker: str) -> list | None:
    """Fetch thesis version history."""
    return api_get(f"/ticker/{ticker}/thesis")


@st.cache_data(ttl=CACHE_TTL_PRICE_HISTORY, show_spinner=False)
def fetch_price_history(ticker: str) -> list[dict] | None:
    """Fetch closing price history (for trend chart)."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/ticker/{ticker}/price-history",
            timeout=API_PRICE_HISTORY_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# Asset Allocation — Cached API Helpers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_TEMPLATES, show_spinner=False)
def fetch_templates() -> list | None:
    """Fetch persona templates."""
    return api_get_silent("/personas/templates")


@st.cache_data(ttl=CACHE_TTL_PROFILE, show_spinner=False)
def fetch_profile() -> dict | None:
    """Fetch active investment profile."""
    return api_get_silent("/profiles")


@st.cache_data(ttl=CACHE_TTL_HOLDINGS, show_spinner=False)
def fetch_holdings() -> list | None:
    """Fetch all holdings."""
    return api_get_silent("/holdings")


@st.cache_data(ttl=CACHE_TTL_REBALANCE, show_spinner=False)
def fetch_rebalance(display_currency: str = "USD") -> dict | None:
    """Fetch rebalance analysis with optional display currency conversion."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/rebalance",
            params={"display_currency": display_currency},
            timeout=API_REBALANCE_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_REBALANCE, show_spinner=False)
def fetch_currency_exposure() -> dict | None:
    """Fetch currency exposure analysis."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/currency-exposure",
            timeout=API_REBALANCE_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# Dashboard — Cached API Helpers
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL_LAST_SCAN, show_spinner=False)
def fetch_last_scan() -> dict | None:
    """Fetch last scan timestamp and market sentiment."""
    return api_get_silent("/scan/last")


@st.cache_data(ttl=CACHE_TTL_FEAR_GREED, show_spinner=False)
def fetch_fear_greed() -> dict | None:
    """Fetch Fear & Greed Index (VIX + CNN composite)."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/market/fear-greed",
            timeout=API_FEAR_GREED_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_PREFERENCES, show_spinner=False)
def fetch_preferences() -> dict | None:
    """Fetch user preferences (privacy mode, etc.)."""
    return api_get_silent("/settings/preferences")


def save_privacy_mode(enabled: bool) -> dict | None:
    """Persist privacy mode to backend (non-cached PUT)."""
    return api_put("/settings/preferences", {"privacy_mode": enabled})


# ---------------------------------------------------------------------------
# Privacy / Masking Helpers (shared across pages)
# ---------------------------------------------------------------------------


def is_privacy() -> bool:
    """Return True when the privacy toggle is active."""
    return bool(st.session_state.get("privacy_mode"))


def on_privacy_change() -> None:
    """Callback: persist privacy mode to backend and backing key."""
    new_val = st.session_state.get("privacy_mode", False)
    st.session_state["_privacy_mode_value"] = new_val
    save_privacy_mode(new_val)


def mask_money(value: float, fmt: str = "${:,.2f}") -> str:
    """Format a monetary value, or return the mask placeholder in privacy mode."""
    if is_privacy():
        return PRIVACY_MASK
    return fmt.format(value)


def mask_qty(value: float, fmt: str = "{:,.4f}") -> str:
    """Format a quantity, or return the mask placeholder in privacy mode."""
    if is_privacy():
        return PRIVACY_MASK
    return fmt.format(value)


# ---------------------------------------------------------------------------
# Rendering Helpers
# ---------------------------------------------------------------------------


def render_thesis_history(history: list[dict]) -> None:
    """Render thesis version history (shared between stock cards and archive)."""
    if history:
        st.markdown("**📜 歷史觀點紀錄：**")
        for entry in history:
            ver = entry.get("version", "?")
            content = entry.get("content", "")
            created = entry.get("created_at", "")
            entry_tags = entry.get("tags", [])
            st.markdown(f"**v{ver}** ({created[:10] if created else '未知日期'})")
            if entry_tags:
                st.caption("標籤：" + " ".join(f"`{t}`" for t in entry_tags))
            st.text(content)
            st.divider()
    else:
        st.caption("尚無歷史觀點紀錄。")


def _render_signal_metrics(signals: dict) -> None:
    """Render technical indicator metrics (price, RSI, MA, bias, volume ratio)."""
    if "error" in signals:
        st.warning(signals["error"])
        return

    price = signals.get("price", "N/A")
    rsi = signals.get("rsi", "N/A")
    ma200 = signals.get("ma200", "N/A")
    ma60 = signals.get("ma60", "N/A")
    bias = signals.get("bias")
    volume_ratio = signals.get("volume_ratio")

    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("現價", f"${price}")
        st.metric("RSI(14)", rsi)
    with metrics_col2:
        st.metric("200MA", f"${ma200}" if ma200 else "N/A")
        st.metric("60MA", f"${ma60}" if ma60 else "N/A")

    chip_col1, chip_col2 = st.columns(2)
    with chip_col1:
        if bias is not None:
            bias_color = (
                "🔴"
                if bias > BIAS_OVERHEATED_UI
                else ("🟢" if bias < BIAS_OVERSOLD_UI else "⚪")
            )
            st.metric(f"{bias_color} 乖離率 Bias", f"{bias}%")
        else:
            st.metric("乖離率 Bias", "N/A")
    with chip_col2:
        if volume_ratio is not None:
            st.metric("量比 Vol Ratio", f"{volume_ratio}x")
        else:
            st.metric("量比 Vol Ratio", "N/A")

    for s in signals.get("status", []):
        st.write(s)

    fetched_at = signals.get("fetched_at")
    if fetched_at:
        browser_tz = st.session_state.get("browser_tz")
        st.caption(f"🕐 資料更新：{format_utc_timestamp(fetched_at, browser_tz)}")


def _render_moat_section(ticker: str, signals: dict) -> None:
    """Render moat health check tab content."""
    moat_data = fetch_moat(ticker)

    if moat_data and moat_data.get("moat") != "N/A":
        curr_margin = moat_data.get("current_margin")
        margin_change = moat_data.get("change")

        if curr_margin is not None and margin_change is not None:
            st.metric(
                "最新毛利率 (Gross Margin)",
                f"{curr_margin:.1f}%",
                delta=f"{margin_change:+.2f} pp (YoY)",
            )
        else:
            st.metric("最新毛利率 (Gross Margin)", "N/A")

        trend = moat_data.get("margin_trend", [])
        valid_trend = [t for t in trend if t.get("value") is not None]
        if valid_trend:
            dates = [t["date"] for t in valid_trend]
            values = [t["value"] for t in valid_trend]

            is_up = values[-1] >= values[0]
            line_color = "#00C805" if is_up else "#FF5252"
            fill_color = "rgba(0,200,5,0.1)" if is_up else "rgba(255,82,82,0.1)"

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode="lines+markers",
                    line=dict(color=line_color, width=2),
                    marker=dict(size=5, color=line_color),
                    fill="tozeroy",
                    fillcolor=fill_color,
                    hovertemplate="%{x}<br>毛利率: %{y:.1f}%<extra></extra>",
                    name="毛利率",
                )
            )

            y_min = min(values)
            y_max = max(values)
            y_range = y_max - y_min
            padding = y_range * 0.05 if y_range > 0 else y_max * 0.02

            fig.update_layout(
                height=PRICE_CHART_HEIGHT,
                margin=dict(l=0, r=0, t=0, b=0),
                yaxis=dict(
                    range=[y_min - padding, y_max + padding],
                    showgrid=True,
                    gridcolor="rgba(128,128,128,0.15)",
                    ticksuffix="%",
                ),
                xaxis=dict(showgrid=False),
                showlegend=False,
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(
                fig, use_container_width=True, config={"displayModeBar": False}
            )
        else:
            st.caption("⚠️ 毛利率趨勢資料不足，無法繪圖。")

        bias_val = signals.get("bias")
        price_is_weak = bias_val is not None and bias_val < PRICE_WEAK_BIAS_THRESHOLD
        margin_is_strong = margin_change is not None and margin_change > 0
        margin_is_bad = (
            margin_change is not None and margin_change < MARGIN_BAD_CHANGE_THRESHOLD
        )

        if margin_is_bad:
            st.error(
                "🔴 **警報 (Thesis Broken)**："
                "護城河受損（毛利 YoY 衰退超過 2 個百分點），"
                "基本面轉差，勿接刀。"
            )
        elif price_is_weak and margin_is_strong:
            st.success(
                "🟢 **錯殺機會 (Contrarian Buy)**："
                "股價回檔但護城河變寬（毛利升），"
                "基本面強勁，可留意佈局時機。"
            )
        elif margin_is_strong:
            st.success("🟢 **護城河穩固**：毛利率 YoY 成長，基本面健康。")
        elif price_is_weak:
            st.warning(
                "🟡 **股價偏弱**：乖離率偏低但護城河數據持平，留意後續季報。"
            )
        else:
            st.info("⚪ **觀察中**：護城河數據持平，持續觀察。")

        details = moat_data.get("details", "")
        if details:
            st.caption(f"📊 {details}")
    else:
        st.warning("⚠️ 無法取得財報數據（可能是新股），請稍後再試。")


def _render_scan_history_section(ticker: str) -> None:
    """Render scan history tab content."""
    scan_hist = fetch_scan_history(ticker)
    if scan_hist:
        latest_sig = scan_hist[0].get("signal", "NORMAL")
        consecutive = 1
        for i in range(1, len(scan_hist)):
            if scan_hist[i].get("signal") == latest_sig:
                consecutive += 1
            else:
                break
        if latest_sig != "NORMAL" and consecutive > 1:
            st.warning(f"⚠️ {latest_sig} 已連續 {consecutive} 次掃描")

        for entry in scan_hist:
            sig = entry.get("signal", "NORMAL")
            scanned = entry.get("scanned_at", "")
            sig_icon = SCAN_SIGNAL_ICONS.get(sig, "⚪")
            date_str = scanned[:16] if scanned else "N/A"
            st.caption(f"{sig_icon} {sig} — {date_str}")
    else:
        st.caption("尚無掃描紀錄。")


def _render_price_alerts_section(ticker: str) -> None:
    """Render price alerts tab content (list + create form)."""
    alerts = fetch_alerts(ticker)
    if alerts:
        st.markdown("**目前警報：**")
        for a in alerts:
            op_str = "<" if a["operator"] == "lt" else ">"
            active_badge = "🟢" if a["is_active"] else "⚪"
            triggered = a.get("last_triggered_at")
            trigger_info = f"（上次觸發：{triggered[:10]}）" if triggered else ""
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.caption(
                    f"{active_badge} {a['metric']} {op_str} "
                    f"{a['threshold']}{trigger_info}"
                )
            with col_b:
                if st.button("🗑️", key=f"del_alert_{a['id']}", help="刪除此警報"):
                    api_delete(f"/alerts/{a['id']}")
                    fetch_alerts.clear()
                    refresh_ui()
        st.divider()

    st.markdown("**➕ 新增警報：**")
    alert_cols = st.columns(3)
    with alert_cols[0]:
        alert_metric = st.selectbox(
            "指標",
            options=["rsi", "price", "bias"],
            key=f"alert_metric_{ticker}",
            label_visibility="collapsed",
        )
    with alert_cols[1]:
        alert_op = st.selectbox(
            "條件",
            options=["lt", "gt"],
            format_func=lambda x: "<（小於）" if x == "lt" else ">（大於）",
            key=f"alert_op_{ticker}",
            label_visibility="collapsed",
        )
    with alert_cols[2]:
        alert_threshold = st.number_input(
            "門檻",
            value=DEFAULT_ALERT_THRESHOLD,
            step=1.0,
            key=f"alert_threshold_{ticker}",
            label_visibility="collapsed",
        )

    if st.button("新增警報", key=f"add_alert_{ticker}"):
        result = api_post(
            f"/ticker/{ticker}/alerts",
            {"metric": alert_metric, "operator": alert_op, "threshold": alert_threshold},
        )
        if result:
            st.success(result.get("message", "✅ 警報已建立"))
            fetch_alerts.clear()
            refresh_ui()


def _render_thesis_editor(ticker: str, stock: dict) -> None:
    """Render thesis history + editor tab content."""
    current_tags = stock.get("current_tags", [])
    history = fetch_thesis_history(ticker)
    render_thesis_history(history or [])

    st.markdown("**✏️ 新增觀點：**")
    new_thesis_content = st.text_area(
        "觀點內容",
        key=f"thesis_input_{ticker}",
        placeholder="寫下你對這檔股票的最新看法...",
        label_visibility="collapsed",
    )

    all_tag_options = sorted(set(DEFAULT_TAG_OPTIONS + current_tags))
    selected_tags = st.multiselect(
        "🏷️ 設定領域標籤",
        options=all_tag_options,
        default=current_tags,
        key=f"tag_select_{ticker}",
    )

    if st.button("更新觀點", key=f"thesis_btn_{ticker}"):
        if new_thesis_content.strip():
            result = api_post(
                f"/ticker/{ticker}/thesis",
                {"content": new_thesis_content.strip(), "tags": selected_tags},
            )
            if result:
                st.success(result.get("message", "✅ 觀點已更新"))
                fetch_thesis_history.clear()
                fetch_stocks.clear()
                refresh_ui()
        else:
            st.warning("⚠️ 請輸入觀點內容。")


def _render_price_chart(ticker: str) -> None:
    """Render interactive price trend chart with 60MA overlay."""
    price_data = fetch_price_history(ticker)
    if price_data and len(price_data) > 5:
        period_tabs = list(PRICE_CHART_PERIODS.keys())
        default_idx = period_tabs.index(PRICE_CHART_DEFAULT_PERIOD)
        period_label = st.radio(
            "趨勢區間",
            period_tabs,
            index=default_idx,
            horizontal=True,
            key=f"chart_period_{ticker}",
            label_visibility="collapsed",
        )
        n_days = PRICE_CHART_PERIODS[period_label]
        sliced = price_data[-n_days:]

        dates = [p["date"] for p in sliced]
        prices = [p["close"] for p in sliced]

        is_up = prices[-1] >= prices[0]
        line_color = "#00C805" if is_up else "#FF5252"
        fill_color = "rgba(0,200,5,0.1)" if is_up else "rgba(255,82,82,0.1)"

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode="lines",
                line=dict(color=line_color, width=2),
                fill="tozeroy",
                fillcolor=fill_color,
                hovertemplate="%{x}<br>$%{y:.2f}<extra></extra>",
                name="收盤價",
            )
        )

        if len(sliced) >= 60:
            df_ma = pd.DataFrame(sliced)
            ma60 = df_ma["close"].rolling(window=60).mean().tolist()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=ma60,
                    mode="lines",
                    line=dict(color="#888", width=1, dash="dot"),
                    name="60MA",
                    hovertemplate="%{x}<br>60MA: $%{y:.2f}<extra></extra>",
                )
            )

        y_min = min(prices)
        y_max = max(prices)
        y_range = y_max - y_min
        padding = y_range * 0.05 if y_range > 0 else y_max * 0.02

        fig.update_layout(
            height=PRICE_CHART_HEIGHT,
            margin=dict(l=0, r=0, t=0, b=0),
            yaxis=dict(
                range=[y_min - padding, y_max + padding],
                showgrid=True,
                gridcolor="rgba(128,128,128,0.15)",
            ),
            xaxis=dict(showgrid=False),
            showlegend=False,
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("📉 價格趨勢資料不足。")


def render_stock_card(stock: dict, enrichment: dict | None = None) -> None:
    """Render a single stock card with technical indicators and thesis editing.

    Args:
        stock: Stock data dict from the /stocks endpoint.
        enrichment: Optional pre-fetched enrichment data from /stocks/enriched.
            When provided, avoids individual API calls for signals, earnings,
            and dividends (lazy-loading optimisation).
    """
    ticker = stock["ticker"]
    cat = stock.get("category", "")

    # Use pre-fetched data when available, otherwise fall back to individual calls
    if enrichment and cat not in SKIP_SIGNALS_CATEGORIES:
        signals = enrichment.get("signals") or {}
    elif cat in SKIP_SIGNALS_CATEGORIES:
        signals = {}
    else:
        signals = fetch_signals(ticker) or {}

    # Build expander header with signal icon, ticker, category, price, and market
    last_signal = stock.get("last_scan_signal", "NORMAL")
    signal_icon = SCAN_SIGNAL_ICONS.get(last_signal, "⚪")
    cat_label_short = CATEGORY_LABELS.get(cat, cat).split("(")[0].strip()
    price = signals.get("price", "")
    price_str = f" | ${price}" if price and price != "N/A" else ""
    market_label = infer_market_label(ticker)
    header = f"{signal_icon} {ticker} — {cat_label_short}{price_str} | {market_label}"

    with st.expander(header, expanded=False):
        col1, col2 = st.columns([1, 2])

        with col1:
            cat_label = CATEGORY_LABELS.get(cat, cat)
            st.caption(f"分類：{cat_label}")

            # Dynamic tags
            current_tags = stock.get("current_tags", [])
            if current_tags:
                tag_badges = " ".join(f"`{tag}`" for tag in current_tags)
                st.markdown(f"🏷️ {tag_badges}")

            _render_signal_metrics(signals)

            # -- Earnings & Dividend (prefer enrichment data) --
            info_cols = st.columns(2)
            if enrichment:
                earnings_data = enrichment.get("earnings")
            else:
                earnings_data = fetch_earnings(ticker)
            earnings_date_str = (
                earnings_data.get("earnings_date") if earnings_data else None
            )
            with info_cols[0]:
                if earnings_date_str:
                    try:
                        ed = dt.strptime(earnings_date_str, "%Y-%m-%d")
                        days_left = (ed - dt.now()).days
                        badge = (
                            f" ({days_left}天)"
                            if 0 < days_left <= EARNINGS_BADGE_DAYS_THRESHOLD
                            else ""
                        )
                        st.caption(f"📅 財報日：{earnings_date_str}{badge}")
                    except ValueError:
                        st.caption(f"📅 財報日：{earnings_date_str}")
                else:
                    st.caption("📅 財報日：N/A")

            with info_cols[1]:
                if cat in ("Moat", "Bond"):
                    if enrichment:
                        div_data = enrichment.get("dividend")
                    else:
                        div_data = fetch_dividend(ticker)
                    if div_data and div_data.get("dividend_yield"):
                        dy = div_data["dividend_yield"]
                        ex_date = div_data.get("ex_dividend_date", "N/A")
                        st.caption(f"💰 殖利率：{dy}% | 除息日：{ex_date}")
                    else:
                        st.caption("💰 殖利率：N/A")

            # -- Sub-sections via tabs --
            _tab_labels = ["🐳 籌碼面", "📈 掃描歷史", "🔔 價格警報"]
            _show_moat = stock.get("category") not in SKIP_MOAT_CATEGORIES
            if _show_moat:
                _tab_labels.insert(1, "🏰 護城河")
            _tabs = st.tabs(_tab_labels)
            _tab_idx = 0

            # -- 13F Institutional Holdings --
            with _tabs[_tab_idx]:
                st.link_button(
                    "🐳 前往 WhaleWisdom 查看大戶動向",
                    WHALEWISDOM_STOCK_URL.format(ticker=ticker.lower()),
                    use_container_width=True,
                )
                st.caption(
                    "💡 投資心法：點擊按鈕查看機構持倉。重點觀察"
                    "波克夏 (Berkshire)、橋水 (Bridgewater) 等大基金"
                    "是 'New Buy/Add' (佈局) 還是 'Sold Out' (離場)。"
                    "跟單要跟「新增」而非庫存。"
                )
                holders = signals.get("institutional_holders")
                if holders and isinstance(holders, list) and len(holders) > 0:
                    st.markdown("**📊 前五大機構持有者：**")
                    st.dataframe(holders, use_container_width=True, hide_index=True)
                else:
                    st.info(
                        "⚠️ 機構持倉資料暫時無法取得，"
                        "請點擊上方按鈕前往 WhaleWisdom 查看完整 13F 報告。"
                    )
            _tab_idx += 1

            if _show_moat:
                with _tabs[_tab_idx]:
                    _render_moat_section(ticker, signals)
                _tab_idx += 1

            with _tabs[_tab_idx]:
                _render_scan_history_section(ticker)
            _tab_idx += 1

            with _tabs[_tab_idx]:
                _render_price_alerts_section(ticker)

        with col2:
            st.markdown("**💡 當前觀點：**")
            st.info(stock.get("current_thesis", "尚無觀點"))

            _render_price_chart(ticker)

            # -- Management tabs --
            _mgmt_tab_thesis, _mgmt_tab_cat, _mgmt_tab_remove = st.tabs(
                ["📝 觀點版控", "🔄 切換分類", "🗑️ 移除追蹤"]
            )

            with _mgmt_tab_thesis:
                _render_thesis_editor(ticker, stock)

            with _mgmt_tab_cat:
                current_cat = stock.get("category", "Growth")
                other_categories = [c for c in CATEGORY_OPTIONS if c != current_cat]
                current_label = CATEGORY_LABELS.get(current_cat, current_cat)
                st.caption(f"目前分類：**{current_label}**")
                new_cat = st.selectbox(
                    "新分類",
                    options=other_categories,
                    format_func=lambda x: CATEGORY_LABELS.get(x, x),
                    key=f"cat_select_{ticker}",
                    label_visibility="collapsed",
                )
                if st.button("確認切換", key=f"cat_btn_{ticker}"):
                    result = api_patch(
                        f"/ticker/{ticker}/category", {"category": new_cat},
                    )
                    if result:
                        st.success(result.get("message", "✅ 分類已切換"))
                        invalidate_stock_caches()
                        refresh_ui()

            with _mgmt_tab_remove:
                st.warning("⚠️ 移除後股票將移至「已移除」分頁，可隨時查閱歷史紀錄。")
                removal_reason = st.text_area(
                    "移除原因",
                    key=f"removal_input_{ticker}",
                    placeholder="寫下你移除這檔股票的原因...",
                    label_visibility="collapsed",
                )
                if st.button("確認移除", key=f"removal_btn_{ticker}", type="primary"):
                    if removal_reason.strip():
                        result = api_post(
                            f"/ticker/{ticker}/deactivate",
                            {"reason": removal_reason.strip()},
                        )
                        if result:
                            st.success(result.get("message", "✅ 已移除"))
                            invalidate_stock_caches()
                            refresh_ui()
                    else:
                        st.warning("⚠️ 請輸入移除原因。")


def render_reorder_section(
    category_key: str, stocks_in_cat: list[dict]
) -> None:
    """Render drag-and-drop reorder section (only when enabled by user)."""
    if len(stocks_in_cat) < REORDER_MIN_STOCKS:
        return
    reorder_on = st.checkbox(
        "↕️ 拖曳排序", key=f"reorder_{category_key}", value=False
    )
    if reorder_on:
        ticker_list = [s["ticker"] for s in stocks_in_cat]
        sorted_tickers = sort_items(ticker_list, key=f"sort_{category_key}")
        if sorted_tickers != ticker_list:
            if st.button("💾 儲存排序", key=f"save_order_{category_key}"):
                result = api_put(
                    "/stocks/reorder", {"ordered_tickers": sorted_tickers}
                )
                if result:
                    st.success("✅ 排序已儲存")
                    fetch_stocks.clear()
                    fetch_enriched_stocks.clear()
                    refresh_ui()
        else:
            st.caption("拖曳股票代號以調整顯示順序。")
