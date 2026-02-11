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
    CATEGORY_LABELS,
    DASHBOARD_ALLOCATION_CHART_HEIGHT,
    DASHBOARD_DRIFT_CHART_HEIGHT,
    DASHBOARD_TOP_HOLDINGS_LIMIT,
    DISPLAY_CURRENCY_OPTIONS,
    FEAR_GREED_DEFAULT_LABEL,
    FEAR_GREED_LABELS,
    HEALTH_SCORE_GOOD_THRESHOLD,
    HEALTH_SCORE_WARN_THRESHOLD,
    MARKET_SENTIMENT_DEFAULT_LABEL,
    MARKET_SENTIMENT_LABELS,
    PRIVACY_MASK,  # still used directly in the holdings table
    PRIVACY_TOGGLE_LABEL,
    SCAN_SIGNAL_ICONS,
)
from utils import (
    fetch_fear_greed,
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

# -- Title row with privacy toggle and refresh button --
_title_cols = st.columns([5, 1, 1])
with _title_cols[0]:
    st.title("📊 投資組合總覽")
with _title_cols[1]:
    st.toggle(PRIVACY_TOGGLE_LABEL, key="privacy_mode", on_change=_on_privacy_change)
with _title_cols[2]:
    if st.button("🔄 重新整理", use_container_width=True):
        invalidate_all_caches()
        refresh_ui()


# ---------------------------------------------------------------------------
# SOP Manual
# ---------------------------------------------------------------------------

with st.expander("📖 投資組合總覽：使用說明書", expanded=False):
    st.markdown("""
### 頁面總覽

本頁面是你的**投資儀表板首頁**，提供一眼式的投資組合健康狀態總覽。所有數據來自系統即時計算，無需手動操作。

---

### 🕐 資料更新時間

頁面頂部顯示兩個時間戳：

- **💰 價格資料更新** — 最近一次透過 yfinance 取得即時股價的時間。對應再平衡分析中的市值計算
- **🔍 上次掃描** — 最近一次執行三層漏斗掃描的時間。掃描每 30 分鐘自動執行一次

> 若兩者時間差距過大，可前往「投資雷達」頁面手動觸發掃描。

---

### KPI 指標列（四個卡片）

| 指標 | 說明 | 如何解讀 |
|------|------|----------|
| **市場情緒** | 基於風向球（Trend Setter）股票是否跌破 60 日均線的比例 | ☀️ 晴天 = 多數風向球在均線之上，市場偏多；🌧️ 雨天 = 超過半數跌破，市場偏空 |
| **總市值** | 所有持倉的市值加總（以選定幣別顯示） | 隱私模式下顯示 `***`。可透過頁面上方幣別選單切換顯示幣別 |
| **健康分數** | 追蹤中股票訊號為「NORMAL」的比例 | ≥ 80% 綠色（健康）、≥ 50% 黃色（留意）、< 50% 紅色（警戒）。分子/分母顯示正常股數與總股數 |
| **追蹤 / 持倉** | 雷達追蹤的股票檔數 vs 實際持倉筆數 | 兩者差距大代表有些追蹤中的股票尚未建立持倉，或持倉中有雷達未追蹤的標的 |

---

### 🎯 目標 vs 實際配置（雙圓餅圖）

並排顯示兩個甜甜圈圖：**左邊是目標配置**（你在投資人格中設定的理想比例），**右邊是實際配置**（當前持倉的市值比例）。兩張圖使用相同的分類顏色，方便直觀對比每個分類是否偏離目標。

---

### 📊 偏移度 Drift（長條圖）

每個分類的**實際配置與目標配置的差距**（百分點）。

- **正值**（向上）= 超配，該分類佔比高於目標
- **負值**（向下）= 低配，該分類佔比低於目標
- 橘色虛線標示 **±5%** 警戒線，超過時長條變紅色
- 展開「💡 再平衡建議」可查看系統自動產生的加減碼建議

---

### ⚠️ 訊號警報

列出所有**訊號非 NORMAL** 的追蹤股票：

| 訊號 | 圖示 | 含義 |
|------|------|------|
| `THESIS_BROKEN` | 🔴 | 護城河受損（毛利率大幅衰退），基本面轉差 |
| `CONTRARIAN_BUY` | 🟢 | RSI 偏低但護城河穩固，可能是錯殺機會 |
| `OVERHEATED` | 🟠 | 乖離率過高，股價短期可能過熱 |

若所有股票均為 NORMAL，會顯示綠色「✅ 所有追蹤股票訊號正常！」。

---

### 🏆 前 10 大持倉

依**權重（佔總市值比例）**排序的前 10 大持倉，顯示股票代號、分類、權重百分比與市值。隱私模式下市值欄位會以 `***` 遮蔽。

> 💡 若單一持倉權重超過 15%，建議留意集中度風險。可前往「個人資產配置」頁的 X-Ray 穿透分析查看更詳細的曝險。

---

### 🙈 隱私模式（跨裝置同步）

右上角的隱私模式開關會遮蔽所有**金額相關數字**（總市值、持倉市值），僅保留百分比與分類結構。設定會儲存至資料庫，跨裝置、跨 session 同步生效。在「個人資產配置」頁面也可切換，兩頁面同步。
""")


# -- Fetch data --
last_scan_data = fetch_last_scan()
stocks_data = fetch_stocks()
holdings_data = fetch_holdings()

# Currency selector (in sidebar-like position, below title)
display_currency = st.selectbox(
    "顯示幣別",
    options=DISPLAY_CURRENCY_OPTIONS,
    index=0,
    key="dashboard_currency",
    label_visibility="collapsed",
)
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
    _ts_parts.append(f"💰 價格資料更新：{price_ts}")

# Last scan timestamp
if last_scan_data and last_scan_data.get("last_scanned_at"):
    scan_ts = format_utc_timestamp(last_scan_data["last_scanned_at"], browser_tz)
    _ts_parts.append(f"🔍 上次掃描：{scan_ts}")

if _ts_parts:
    st.caption(" ｜ ".join(_ts_parts))
else:
    st.caption("⏳ 尚無資料更新紀錄")


# ---------------------------------------------------------------------------
# Section 1: KPI Metrics Row
# ---------------------------------------------------------------------------
kpi_cols = st.columns(5)

# -- 1a. Market Sentiment --
with kpi_cols[0]:
    market_status = (last_scan_data or {}).get("market_status")
    if market_status and market_status in MARKET_SENTIMENT_LABELS:
        sentiment_info = MARKET_SENTIMENT_LABELS[market_status]
        st.metric("市場情緒", sentiment_info["label"])
        details = (last_scan_data or {}).get("market_status_details", "")
        if details:
            st.caption(details)
    else:
        st.metric("市場情緒", MARKET_SENTIMENT_DEFAULT_LABEL)

# -- 1b. Fear & Greed Index --
with kpi_cols[1]:
    fear_greed_data = fetch_fear_greed()
    if fear_greed_data:
        fg_level = fear_greed_data.get("composite_level", "N/A")
        fg_score = fear_greed_data.get("composite_score", 50)
        fg_info = FEAR_GREED_LABELS.get(fg_level, FEAR_GREED_LABELS["N/A"])
        vix_data = fear_greed_data.get("vix") or {}
        vix_val = vix_data.get("value")
        vix_change = vix_data.get("change_1d")
        st.metric(
            "恐懼貪婪",
            fg_info["label"],
            delta=f"分數 {fg_score}/100",
            delta_color=fg_info["color"],
        )
        vix_parts = []
        if vix_val is not None:
            vix_parts.append(f"VIX={vix_val:.1f}")
        if vix_change is not None:
            vix_parts.append(f"{'▲' if vix_change > 0 else '▼'}{abs(vix_change):.1f}")
        if vix_parts:
            st.caption(" ".join(vix_parts))
    else:
        st.metric("恐懼貪婪", FEAR_GREED_DEFAULT_LABEL)

# -- 1c. Total Portfolio Value --
with kpi_cols[2]:
    if rebalance_data and rebalance_data.get("total_value") is not None:
        total_val = rebalance_data["total_value"]
        st.metric("總市值", _mask_money(total_val))
    else:
        st.metric("總市值", "N/A")

# -- 1d. Health Score --
with kpi_cols[3]:
    health_pct, normal_cnt, total_cnt = _compute_health_score(stocks_data or [])
    if total_cnt > 0:
        st.metric(
            "健康分數",
            f"{health_pct:.0f}%",
            delta=f"{normal_cnt}/{total_cnt} 正常",
            delta_color=_health_color(health_pct),
        )
    else:
        st.metric("健康分數", "N/A")

# -- 1e. Tracking & Holdings Count --
with kpi_cols[4]:
    stock_count = len(stocks_data) if stocks_data else 0
    holding_count = len(holdings_data) if holdings_data else 0
    st.metric("追蹤 / 持倉", f"{stock_count} 檔 / {holding_count} 筆")


# ---------------------------------------------------------------------------
# Section 2: Allocation at a Glance
# ---------------------------------------------------------------------------
st.divider()

if rebalance_data and profile_data and rebalance_data.get("categories"):
    breakdown = rebalance_data["categories"]

    # -- 2a. Dual Donut Chart: Target vs Actual (side by side) --
    st.subheader("🎯 目標 vs 實際配置")

    target_alloc = profile_data.get("config", {})
    cat_labels = []
    target_vals = []
    actual_vals = []
    colors = []

    for cat_key, target_pct in target_alloc.items():
        cat_display = CATEGORY_LABELS.get(cat_key, cat_key)
        icon = CATEGORY_ICON_SHORT.get(cat_key, "")
        cat_labels.append(f"{icon} {cat_display.split('(')[0].strip()}")
        target_vals.append(target_pct)
        cat_info = breakdown.get(cat_key, {})
        actual_vals.append(cat_info.get("current_pct", 0))
        colors.append(CATEGORY_COLOR_MAP.get(cat_key, CATEGORY_COLOR_FALLBACK))

    fig_alloc = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "pie"}, {"type": "pie"}]],
        subplot_titles=["🎯 目標配置", "📊 實際配置"],
    )

    # Left donut — Target allocation
    fig_alloc.add_trace(
        go.Pie(
            labels=cat_labels,
            values=target_vals,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo="label+percent",
            textposition="auto",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "目標佔比：%{percent}<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    # Right donut — Actual allocation
    fig_alloc.add_trace(
        go.Pie(
            labels=cat_labels,
            values=actual_vals,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo="label+percent",
            textposition="auto",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "實際佔比：%{percent}<extra></extra>"
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

    # -- 2b. Drift Bar Chart --
    st.subheader("📊 偏移度 Drift")
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
        height=DASHBOARD_DRIFT_CHART_HEIGHT,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis_title="偏移 (%)",
        showlegend=False,
    )
    st.plotly_chart(fig_drift, use_container_width=True, config={"displayModeBar": False})

    # Rebalance advice summary
    advice = rebalance_data.get("advice", [])
    if advice:
        with st.expander("💡 再平衡建議", expanded=False):
            for item in advice[:5]:
                st.write(item)
else:
    st.info("📈 尚無配置資料。請先設定投資人格並新增持倉。")


# ---------------------------------------------------------------------------
# Section 3: Signal Alerts
# ---------------------------------------------------------------------------
st.divider()
st.subheader("⚠️ 訊號警報")

if stocks_data:
    alert_stocks = [
        s for s in stocks_data
        if s.get("is_active", True) and s.get("last_scan_signal", "NORMAL") != "NORMAL"
    ]
    if alert_stocks:
        for s in alert_stocks:
            signal = s.get("last_scan_signal", "NORMAL")
            icon = SCAN_SIGNAL_ICONS.get(signal, "⚪")
            cat_label = CATEGORY_LABELS.get(s.get("category", ""), s.get("category", ""))
            cat_short = cat_label.split("(")[0].strip()
            st.markdown(f"{icon} **{s['ticker']}** — {cat_short} — `{signal}`")
    else:
        st.success("✅ 所有追蹤股票訊號正常！")
else:
    st.caption("尚未追蹤任何股票。")


# ---------------------------------------------------------------------------
# Section 4: Top Holdings
# ---------------------------------------------------------------------------
st.divider()
st.subheader(f"🏆 前 {DASHBOARD_TOP_HOLDINGS_LIMIT} 大持倉")

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
        rows.append({
            "股票": h.get("ticker", ""),
            "分類": f"{icon} {cat}",
            "權重": f"{h.get('weight_pct', 0):.1f}%",
            "市值": PRIVACY_MASK if privacy else f"${h.get('market_value', 0):,.2f}",
        })

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("無持倉資料。")
else:
    st.info("📊 尚無持倉資料。請先新增持倉以查看分析。")
