"""
FX Watch — 外匯換匯時機監控
提供使用者自訂外匯監控配置，並接收換匯時機警報。
"""

import streamlit as st
import requests
from datetime import datetime

from config import (
    BACKEND_URL,
    API_POST_TIMEOUT,
    API_PATCH_TIMEOUT,
    API_DELETE_TIMEOUT,
    FX_CURRENCY_OPTIONS,
    PRIVACY_TOGGLE_LABEL,
)
from utils import (
    fetch_fx_watches,
    invalidate_fx_watch_caches,
    refresh_ui as _refresh_ui,
    is_privacy as _is_privacy,
    on_privacy_change as _on_privacy_change,
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
        FX_CHART_PERIODS,
        FX_CHART_DEFAULT_PERIOD,
    )
    from utils import fetch_fx_history

    # Fetch data
    fx_data = fetch_fx_history(base, quote)

    if not fx_data or len(fx_data) < 5:
        st.caption("📉 匯率歷史資料不足（需至少 5 個交易日）。")
        return

    # Period selection (horizontal radio buttons)
    period_label = st.radio(
        "趨勢區間",
        list(FX_CHART_PERIODS.keys()),
        index=list(FX_CHART_PERIODS.keys()).index(FX_CHART_DEFAULT_PERIOD),
        horizontal=True,
        key=f"fx_chart_period_{watch_id}",
        label_visibility="collapsed",
    )

    # Slice data to selected period (client-side filtering, no re-fetch)
    n_days = FX_CHART_PERIODS[period_label]
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
            hovertemplate="%{x}<br>匯率: %{y:.4f}<extra></extra>",
        )
    )

    # Add recent high reference line (if sufficient data)
    if len(sliced) >= recent_high_days:
        recent_high = max(d["close"] for d in sliced[-recent_high_days:])
        fig.add_hline(
            y=recent_high,
            line_dash="dash",
            line_color="#FFA500",  # Orange
            annotation_text=f"{recent_high_days}日高點: {recent_high:.4f}",
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
    st.title("💱 外匯換匯時機監控")
    st.caption("設定外匯監控配置，當匯率接近高點或連續上漲時自動發送 Telegram 通知")

with _title_cols[1]:
    st.toggle(PRIVACY_TOGGLE_LABEL, key="privacy_mode", on_change=_on_privacy_change)

# Usage manual (collapsible)
with st.expander("📖 使用說明"):
    st.markdown("""
    ### 功能說明

    **外匯換匯時機監控** 提供完整的換匯時機管理與分析系統：

    1. **近期高點偵測**：當匯率接近 N 日內的歷史高點時發出警報（預設容差 2%）
    2. **連續上漲追蹤**：當匯率連續上漲 N 日時發出警報（預設 3 日）
    3. **彈性條件組合**：可獨立啟用/停用兩種偵測條件（OR 邏輯）
    4. **智慧冷卻機制**：避免重複通知，預設 24 小時內同一配置不重複警報
    5. **即時換匯建議**：監控表格直接顯示 AI 分析建議與推薦理由
    6. **互動式趨勢圖**：3 個月歷史匯率走勢，視覺化參考線與期間選擇

    ### 使用流程

    **步驟 1：新增監控配置**
    1. 點擊左側 **➕ 新增監控配置** 展開設定表單
    2. 選擇貨幣對：基礎貨幣（持有的貨幣）→ 報價貨幣（想兌換成的貨幣）
       - 例如：持有 USD 想換 TWD → 選擇 USD/TWD
       - 支援 9 種貨幣：USD、TWD、JPY、EUR、GBP、CNY、HKD、SGD、THB
    3. 調整偵測條件：
       - **近期高點回溯天數**（5-90 日）：判斷「近期高點」的回溯期間
       - **連續上漲天數門檻**（2-10 日）：連續上漲多少天後警報
    4. 設定警報開關：
       - **啟用近期高點警報**：匯率接近高點時提醒
       - **啟用連續上漲警報**：連續上漲達門檻時提醒
       - 至少須啟用一項（兩項可同時啟用，任一條件滿足即警報）
    5. 設定提醒間隔（1-168 小時）：同一配置在此期間內不重複發送警報
    6. 點擊 **➕ 新增監控** 完成設定

    **步驟 2：查看監控配置與換匯建議**
    - **監控配置列表**：顯示所有配置的詳細參數
    - **換匯建議欄位**：即時顯示 AI 分析結果
      - 🟢 **建議換匯**：當前匯率符合換匯條件（接近高點或連續上漲）
      - ⚪ **暫不換匯**：當前匯率未達換匯條件，建議持續觀察
      - ⏳ **分析中...**：系統正在計算分析結果
    - **換匯分析詳情**：展開查看詳細推薦理由、當前匯率、檢測參數

    **步驟 3：查看匯率趨勢圖**
    1. 在 **📈 匯率趨勢圖** 區塊，展開想查看的貨幣對
    2. 趨勢圖特色：
       - **3 個月歷史資料**：顯示近 90 個交易日的收盤匯率
       - **期間選擇**：點選 1 個月 / 2 個月 / 3 個月 切換顯示區間（無需重新載入）
       - **顏色編碼**：
         - 🟢 **綠色**：期間內匯率上漲（期末 ≥ 期初）
         - 🔴 **紅色**：期間內匯率下跌（期末 < 期初）
       - **參考線**：橘色虛線標示「N 日高點」位置（N = 您設定的回溯天數）
       - **懸停提示**：滑鼠移到圖表上顯示日期與精確匯率（4 位小數）
    3. 圖表下方顯示監控設定、警報狀態、最後警報時間

    **步驟 4：管理監控配置**
    - **快速操作區塊**：每個配置有內嵌操作按鈕
      - 🟢 **啟用** / 🔴 **停用**：切換配置的啟用狀態（停用後不檢查、不警報）
      - 🗑️ **刪除**：移除配置（無法復原，需重新建立）
    - 操作後自動重新整理頁面，立即生效

    ### 進階功能

    **🔍 手動檢查**
    - 功能：立即分析所有啟用中的監控配置，產出換匯建議
    - 用途：快速查看當前市場是否有換匯機會
    - 特性：**不發送 Telegram 通知**，僅在頁面顯示結果
    - 結果顯示：
      - 🎯 綠色方框：建議換匯（should_alert = true）
      - 💡 藍色方框：暫不換匯（should_alert = false）
      - 包含詳細推薦理由、當前匯率

    **📨 立即發送警報**
    - 功能：檢查所有啟用中的配置，發送 Telegram 換匯警報
    - 用途：手動觸發通知（例如想立即收到當前建議）
    - 特性：
      - **受冷卻機制限制**：若某配置在提醒間隔內已發送過，不會重複發送
      - 顯示統計：總監控數、觸發警報數、實際發送數
      - 列出所有觸發警報的貨幣對與建議內容
    - 差異：手動檢查不發通知，立即警報會發 Telegram

    **🔒 隱私模式**
    - 功能：一鍵隱藏匯率趨勢圖
    - 用途：展示畫面、截圖分享時保護資訊
    - 開啟方式：點擊右上角 **🙈 隱私模式** 切換開關
    - 影響範圍：整個趨勢圖區塊隱藏，其他資訊（表格、建議）不受影響

    ### 常見問題

    **Q：如何判斷現在是否該換匯？**
    A：查看「換匯建議」欄位：
    - 🟢 建議換匯 → 匯率符合您設定的條件（接近高點或連續上漲），可考慮換匯
    - ⚪ 暫不換匯 → 匯率未達條件，建議持續觀察

    **Q：為什麼我的配置顯示「暫不換匯」但匯率很高？**
    A：系統判斷基於您設定的參數（回溯天數、連續上漲門檻）。若匯率雖高但未達「近期高點」（例如 30 日內更高）或未連續上漲，仍會顯示暫不換匯。可調整參數或查看趨勢圖自行判斷。

    **Q：「手動檢查」和「立即發送警報」有什麼差別？**
    A：
    - **手動檢查**：僅在頁面顯示分析結果，不發 Telegram 通知（適合快速查看）
    - **立即發送警報**：分析後發送 Telegram 通知（適合想收到推送提醒）

    **Q：我可以監控多少個貨幣對？**
    A：無上限，但建議聚焦在實際需要的貨幣對（例如常用的 USD/TWD、JPY/TWD），避免警報過多。

    **Q：系統多久自動檢查一次？**
    A：後端定時任務每 6 小時自動檢查一次所有啟用中的配置，若符合條件且未在冷卻期內，自動發送 Telegram 警報（見 docker-compose.yml 設定）。

    **Q：為什麼我刪除配置後還收到通知？**
    A：可能是刪除前已觸發警報但尚未發送。請確認 Telegram 通知時間戳，若在刪除後則可能是緩存問題，請重新整理頁面。
    """)

# ---------------------------------------------------------------------------
# Edit Watch Popover
# ---------------------------------------------------------------------------

def edit_watch_popover(watch: dict):
    """Popover for editing watch configuration inline."""
    with st.popover("⚙️ 編輯", use_container_width=True):
        st.markdown(f"**編輯 {watch['base_currency']}/{watch['quote_currency']}**")

        # Detection settings
        recent_high_days = st.slider(
            "近期高點回溯天數",
            min_value=5,
            max_value=90,
            value=watch["recent_high_days"],
            step=5,
            key=f"edit_recent_{watch['id']}"
        )

        consecutive_days = st.slider(
            "連續上漲天數門檻",
            min_value=2,
            max_value=10,
            value=watch["consecutive_increase_days"],
            step=1,
            key=f"edit_consec_{watch['id']}"
        )

        st.divider()

        # Alert toggles
        alert_on_high = st.checkbox(
            "啟用近期高點警報",
            value=watch["alert_on_recent_high"],
            key=f"edit_high_{watch['id']}"
        )

        alert_on_consecutive = st.checkbox(
            "啟用連續上漲警報",
            value=watch["alert_on_consecutive_increase"],
            key=f"edit_consecutive_{watch['id']}"
        )

        reminder_hours = st.number_input(
            "提醒間隔（小時）",
            min_value=1,
            max_value=168,
            value=watch["reminder_interval_hours"],
            step=1,
            key=f"edit_reminder_{watch['id']}"
        )

        st.divider()

        # Save button
        if st.button("💾 儲存變更", key=f"save_edit_{watch['id']}", use_container_width=True):
            # Validation
            if not alert_on_high and not alert_on_consecutive:
                st.warning("⚠️ 至少要啟用一項警報條件")
            else:
                payload = {
                    "recent_high_days": recent_high_days,
                    "consecutive_increase_days": consecutive_days,
                    "alert_on_recent_high": alert_on_high,
                    "alert_on_consecutive_increase": alert_on_consecutive,
                    "reminder_interval_hours": reminder_hours,
                }

                try:
                    resp = requests.patch(
                        f"{BACKEND_URL}/fx-watch/{watch['id']}",
                        json=payload,
                        timeout=API_PATCH_TIMEOUT,
                    )
                    if resp.ok:
                        st.success("✅ 已更新")
                        invalidate_fx_watch_caches()
                        _refresh_ui()
                    else:
                        st.error(f"❌ 更新失敗：{resp.text}")
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")


# ---------------------------------------------------------------------------
# Add Watch Dialog
# ---------------------------------------------------------------------------

@st.dialog("➕ 新增監控配置", width="large")
def add_watch_dialog():
    """Dialog for adding a new FX watch configuration."""
    with st.form("add_fx_watch_form", clear_on_submit=False):
        # Currency pair (2-column layout)
        # NOTE: Both selectboxes use the FULL options list because st.form
        # does not rerun on widget change — dynamic filtering would cause
        # index drift between the rendered options and submitted values.
        col_base, col_quote = st.columns(2)
        with col_base:
            base_currency = st.selectbox(
                "基礎貨幣",
                options=FX_CURRENCY_OPTIONS,
                index=0,  # USD
                help="您想兌換的貨幣（例如持有 USD 想換成 TWD）",
                key="add_dialog_base"
            )

        with col_quote:
            quote_currency = st.selectbox(
                "報價貨幣",
                options=FX_CURRENCY_OPTIONS,
                index=1,  # TWD
                help="您想兌換成的貨幣（必須與基礎貨幣不同）",
                key="add_dialog_quote"
            )

        st.divider()

        # Detection settings (2-column layout)
        col_recent, col_consec = st.columns(2)
        with col_recent:
            recent_high_days = st.slider(
                "近期高點回溯天數",
                min_value=5,
                max_value=90,
                value=30,
                step=5,
                help="判斷「近期高點」的回溯天數"
            )

        with col_consec:
            consecutive_days = st.slider(
                "連續上漲天數門檻",
                min_value=2,
                max_value=10,
                value=3,
                step=1,
                help="連續上漲多少天後發出警報"
            )

        st.divider()

        # Alert toggles (2-column layout)
        col_toggle1, col_toggle2 = st.columns(2)
        with col_toggle1:
            alert_on_high = st.checkbox(
                "啟用近期高點警報",
                value=True,
                help="當匯率接近近期高點時發送警報"
            )

        with col_toggle2:
            alert_on_consecutive = st.checkbox(
                "啟用連續上漲警報",
                value=True,
                help="當匯率連續上漲達門檻時發送警報"
            )

        # Reminder interval
        reminder_hours = st.number_input(
            "提醒間隔（小時）",
            min_value=1,
            max_value=168,
            value=24,
            step=1,
            help="避免重複通知，同一配置在此時間內不重複警報"
        )

        st.divider()

        # Submit buttons
        col_submit, col_cancel = st.columns([1, 1])
        with col_submit:
            submitted = st.form_submit_button("✅ 新增監控", use_container_width=True, type="primary")
        with col_cancel:
            cancelled = st.form_submit_button("❌ 取消", use_container_width=True)

        if cancelled:
            st.session_state["show_add_dialog"] = False
            st.rerun()

        if submitted:
            # Validation
            if base_currency == quote_currency:
                st.error("⚠️ 基礎貨幣與報價貨幣不能相同")
            elif not alert_on_high and not alert_on_consecutive:
                st.warning("⚠️ 至少要啟用一項警報條件")
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

                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/fx-watch",
                        json=payload,
                        timeout=API_POST_TIMEOUT,
                    )
                    if resp.ok:
                        st.success(f"✅ 已新增 {base_currency}/{quote_currency} 監控")
                        invalidate_fx_watch_caches()
                        st.session_state["show_add_dialog"] = False
                        st.rerun()
                    else:
                        st.error(f"❌ 新增失敗：{resp.text}")
                except Exception as e:
                    st.error(f"❌ 新增失敗：{e}")

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
    st.metric("總監控數", len(watches) if watches else 0)

with top_row[1]:
    active_count = sum(1 for w in watches if w.get("is_active", False)) if watches else 0
    st.metric("啟用中", active_count)

with top_row[2]:
    # Show last alert time from most recent watch
    if watches:
        last_times = [
            w.get("last_alerted_at")
            for w in watches
            if w.get("last_alerted_at")
        ]
        if last_times:
            latest = max(last_times)
            st.metric("最後警報", datetime.fromisoformat(latest).strftime("%m/%d %H:%M"))
        else:
            st.metric("最後警報", "尚未發送")
    else:
        st.metric("最後警報", "—")

with top_row[3]:
    # Manual check button (disabled if no watches)
    if st.button("🔍 檢查", use_container_width=True, help="立即分析所有監控配置（不發送通知）", disabled=not watches):
        with st.spinner("分析中..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/fx-watch/check",
                    timeout=API_POST_TIMEOUT,
                )
                if resp.ok:
                    data = resp.json()
                    st.success(f"✅ 已完成 {data.get('total_watches', 0)} 筆監控分析")
                    invalidate_fx_watch_caches()
                    _refresh_ui()
                else:
                    st.error(f"❌ 檢查失敗：{resp.text}")
            except Exception as e:
                st.error(f"❌ 檢查失敗：{e}")

with top_row[4]:
    # Instant alert button (disabled if no watches)
    if st.button("📨 警報", use_container_width=True, help="手動觸發 Telegram 通知（受冷卻機制限制）", disabled=not watches):
        with st.spinner("發送中..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/fx-watch/alert",
                    timeout=API_POST_TIMEOUT,
                )
                if resp.ok:
                    data = resp.json()
                    st.success(
                        f"✅ {data.get('triggered_alerts', 0)} 筆觸發，{data.get('sent_alerts', 0)} 筆已發送"
                    )
                    invalidate_fx_watch_caches()
                    _refresh_ui()
                else:
                    st.error(f"❌ 發送失敗：{resp.text}")
            except Exception as e:
                st.error(f"❌ 發送失敗：{e}")

with top_row[5]:
    # Add watch button (always enabled)
    if st.button("➕ 新增", use_container_width=True, type="primary", help="新增外匯監控配置"):
        # Clear any existing form state to ensure clean dialog
        for key in list(st.session_state.keys()):
            if key.startswith("add_dialog_"):
                del st.session_state[key]
        st.session_state["show_add_dialog"] = True
        st.rerun()

st.divider()

# Show add dialog if flag is set
if st.session_state.get("show_add_dialog", False):
    add_watch_dialog()

# Empty state check
if not watches:
    st.info("📭 尚未設定任何監控配置，請點擊上方「➕ 新增」按鈕開始")
    st.stop()

# Fetch real-time analysis for all watches
@st.cache_data(ttl=60, show_spinner=False)
def fetch_fx_watch_analysis() -> dict[int, dict]:
    """
    Fetch real-time FX analysis for all active watches.
    Returns mapping of watch_id -> {recommendation, reasoning, should_alert}
    """
    try:
        resp = requests.post(
            f"{BACKEND_URL}/fx-watch/check",
            timeout=API_POST_TIMEOUT,
        )
        if resp.ok:
            data = resp.json()
            results = data.get("results", [])
            # Create watch_id -> analysis mapping
            return {
                r["watch_id"]: {
                    "recommendation": r["result"]["recommendation_zh"],
                    "reasoning": r["result"]["reasoning_zh"],
                    "should_alert": r["result"]["should_alert"],
                    "current_rate": r["result"]["current_rate"],
                }
                for r in results
            }
        return {}
    except Exception:
        return {}

# Get analysis data
analysis_map = fetch_fx_watch_analysis()

# ---------------------------------------------------------------------------
# Unified Card Layout (one card per watch)
# ---------------------------------------------------------------------------

st.subheader("📋 監控配置")

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
        badge = "⏳ 分析中..."

    status_icon = "🟢" if is_active else "🔴"
    expander_title = f"{status_icon} 💱 {pair} — {rate_str} — {badge}"

    # Collapsible card
    with st.expander(expander_title, expanded=False):
        # Quick action row at top
        action_cols = st.columns([1, 1, 1, 3])

        with action_cols[0]:
            # Status toggle
            toggle_label = "🔴 停用" if is_active else "🟢 啟用"
            if st.button(
                toggle_label,
                key=f"toggle_{watch_id}",
                use_container_width=True,
                help="啟用/停用監控"
            ):
                try:
                    resp = requests.patch(
                        f"{BACKEND_URL}/fx-watch/{watch_id}",
                        json={"is_active": not is_active},
                        timeout=API_PATCH_TIMEOUT,
                    )
                    if resp.ok:
                        invalidate_fx_watch_caches()
                        _refresh_ui()
                except Exception:
                    pass

        with action_cols[1]:
            edit_watch_popover(watch)

        with action_cols[2]:
            if st.button("🗑️ 刪除", key=f"delete_{watch_id}", use_container_width=True):
                try:
                    resp = requests.delete(
                        f"{BACKEND_URL}/fx-watch/{watch_id}",
                        timeout=API_DELETE_TIMEOUT,
                    )
                    if resp.ok:
                        invalidate_fx_watch_caches()
                        _refresh_ui()
                except Exception:
                    pass

        st.divider()

        # Body: Chart (left) + Analysis (right) - 2 column layout
        if not _is_privacy():
            body_cols = st.columns([3, 2])

            with body_cols[0]:
                # Chart
                _render_fx_chart(
                    watch["base_currency"],
                    watch["quote_currency"],
                    watch["recent_high_days"],
                    watch_id,
                )

            with body_cols[1]:
                # Analysis reasoning
                if analysis:
                    reasoning = analysis.get("reasoning", "")
                    st.markdown("**📊 分析原因**")
                    st.caption(reasoning)
                else:
                    st.caption("⏳ 等待分析...")

                st.divider()

                # Config summary
                st.markdown("**⚙️ 監控設定**")
                st.caption(f"• 近期高點: {watch['recent_high_days']} 日")
                st.caption(f"• 連續上漲: {watch['consecutive_increase_days']} 日")
                st.caption(f"• 間隔: {watch['reminder_interval_hours']} 小時")

                high_icon = "✅" if watch["alert_on_recent_high"] else "❌"
                consec_icon = "✅" if watch["alert_on_consecutive_increase"] else "❌"
                st.caption(f"• 高點警報: {high_icon}")
                st.caption(f"• 上漲警報: {consec_icon}")

                # Last alert
                last_alert = watch.get("last_alerted_at")
                if last_alert:
                    alert_time = datetime.fromisoformat(last_alert).strftime("%Y-%m-%d %H:%M")
                    st.caption(f"• 最後警報: {alert_time}")
                else:
                    st.caption("• 最後警報: 尚未發送")
        else:
            # Privacy mode: hide chart and analysis
            st.info("🔒 隱私模式已啟用，圖表與分析已隱藏。")

st.divider()
