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
    CASH_ACCOUNT_TYPE_OPTIONS,
    CASH_CURRENCY_OPTIONS,
    CATEGORY_LABELS,
    HOLDING_IMPORT_TEMPLATE,
    HOLDINGS_EXPORT_FILENAME,
    PRIVACY_TOGGLE_LABEL,
    STOCK_CATEGORY_OPTIONS,
    STOCK_MARKET_OPTIONS,
    STOCK_MARKET_PLACEHOLDERS,
)
from utils import (
    api_get_silent,
    api_post,
    api_put,
    build_radar_lookup,
    fetch_holdings,
    fetch_preferences,
    fetch_profile,
    fetch_templates,
    invalidate_all_caches,
    invalidate_holding_caches,
    invalidate_stock_caches,
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
# Helpers (sidebar-only)
# ---------------------------------------------------------------------------

_MARKET_KEYS = list(STOCK_MARKET_OPTIONS.keys())


def _market_label(key: str) -> str:
    return STOCK_MARKET_OPTIONS[key]["label"]


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------

_title_cols = st.columns([5, 1])
with _title_cols[0]:
    st.title("💼 個人資產配置")
    st.caption("持倉記錄 · 再平衡分析 · Telegram 通知")
with _title_cols[1]:
    st.toggle(PRIVACY_TOGGLE_LABEL, key="privacy_mode", on_change=_on_privacy_change)


# ---------------------------------------------------------------------------
# SOP Manual
# ---------------------------------------------------------------------------

with st.expander("📖 個人資產配置：使用說明書", expanded=False):
    st.markdown("""
### 頁面總覽

本頁面負責**個人資產持倉管理**與**投資組合再平衡分析**。透過左側導覽列從投資雷達切換至此頁面。

### 🙈 隱私模式（跨裝置同步）

頁面右上角提供**隱私模式開關**。開啟後，所有敏感的金額數字（總市值、持倉數量、現價、平均成本、市值等）會以 `***` 遮蔽，僅保留百分比與分類結構。適合螢幕分享或截圖時使用，不影響後端資料。**隱私模式設定會儲存至資料庫**，跨裝置、跨瀏覽器 session 同步生效。在「投資組合總覽」頁面也可切換，兩頁面同步。

---

### 側邊欄 — 新增持倉（三種模式）

透過「資產類型」切換，可新增三種持倉：

- **📈 股票**：選擇市場（🇺🇸 美股 / 🇹🇼 台股 / 🇯🇵 日股 / 🇭🇰 港股），輸入股票代號（系統自動加上市場後綴如 `.TW`、`.T`），選擇分類，輸入股數、平均成本與券商
- **🛡️ 債券**：輸入債券代號（如 TLT、BND），選擇幣別，輸入股數、平均成本與券商
- **💵 現金**：選擇幣別與金額，可選填銀行、帳戶類型（活存/定存/貨幣市場基金）及備註

#### 雷達自動同步

- 若輸入的股票代號**已在雷達追蹤**中，分類欄位會自動帶入雷達中的分類（鎖定不可修改）
- 若輸入的是**全新股票**，新增持倉後系統會自動將其加入雷達追蹤，可選填投資觀點作為初始紀錄

側邊欄也提供**匯出 / 匯入持倉**功能（JSON 格式），以及匯入範本下載。

---

### Step 1 — 設定目標配置

- 從 6 種預設**投資人格範本**中選擇（退休防禦、標準型、積極進攻、槓鈴策略、狙擊手、自訂）
- 每種範本預設五大分類的目標配置比例
- 可隨時**微調**各分類百分比（合計需等於 100%）
- 已選定範本後，可點擊**「🔄 切換風格」**更換為其他範本

---

### Step 2 — 持倉管理

- 持倉表格支援**即時編輯**：直接點擊儲存格即可修改數量、平均成本、券商、分類
- 編輯完成後按下「💾 儲存變更」即可批次更新
- 可透過下拉選單選擇持倉並按「🗑️ 刪除」移除
- 新增持倉請使用左側面板

---

### Step 3 — 再平衡分析

- **載入指示器**：載入再平衡資料時顯示「📊 載入再平衡分析中...」狀態動畫，完成後自動收合為「✅ 再平衡分析載入完成」
- **資料更新時間**：幣別選單旁顯示資料取得時間（🕐），自動偵測瀏覽器時區並以本地時間顯示，讓你清楚知道數據的新鮮度
- **幣別切換**：透過下拉選單選擇顯示幣別（USD / TWD / JPY / EUR / GBP / CNY / HKD / SGD / THB），所有資產市值將自動以選定幣別計算
- **即時匯率**：系統透過 yfinance 取得即時匯率（快取 1 小時），確保跨幣別資產正確換算
- **雙餅圖**：目標配置 vs 實際配置
- **Drift 長條圖**：各分類的偏移程度（紅色超配 / 綠色低配）
- **個股持倉明細**：顯示各股原始幣別、數量、現價、平均成本、換算後市值與佔比
- **再平衡建議**：自動提示偏移超過 5% 的分類，建議加碼或減碼
- **🔬 穿透式 X-Ray**：自動解析 ETF 前 10 大成分股，計算「直接持倉 + ETF 間接曝險」的真實比例。堆疊長條圖直觀顯示集中度風險，超過 15% 門檻時以橘色警告提示，亦可一鍵發送 Telegram 警告

> 💡 定期（如每季）檢視資產配置，是最重要但最常被忽略的投資紀律。

---

### Step 4 — 匯率曝險監控 (Currency Exposure Monitor)

- **本幣設定**：在 Step 4 區域右上角可直接切換本幣（如 TWD → USD），系統會以此作為匯率曝險計算的基準
- **雙分頁檢視**：
  - **💵 現金幣別曝險**（預設）：僅分析現金部位的幣別分佈，匯率風險對現金的影響最直接
  - **📊 全資產幣別曝險**：分析整體投資組合（含股票、債券、現金）的幣別分佈
- **幣別分佈餅圖**：以甜甜圈圖顯示各幣別的市值比例
- **風險等級**：根據匯率變動警報嚴重程度自動判定
  - 🟢 低風險：無顯著匯率警報
  - 🟡 中風險：偵測到短期（5 日）波段變動
  - 🔴 高風險：偵測到單日劇烈波動
- **近期匯率變動**：顯示各外幣對本幣的近 5 日匯率變動百分比，以 📈📉 標示方向
- **匯率變動警報**：三層級偵測（🔴 單日 >1.5% / 🟡 5日 >2% / 🔵 3月 >8%），以色彩標籤分級顯示
- **智慧建議**：系統會特別標示現金部位受匯率影響的金額，幫助您聚焦最需要關注的部分
- **Telegram 警報**：當匯率變動超過三層門檻時發送 Telegram 通知（含現金曝險金額）。系統每 6 小時自動檢查，亦可手動點擊「📨 發送匯率曝險警報至 Telegram」

---

### Step 5 — 聰明提款（Smart Withdrawal）

當你需要從投資組合中提取現金時，系統會透過 **Liquidity Waterfall** 三層優先演算法，自動建議最佳賣出方案：

1. **🔄 再平衡**（Priority 1）：優先賣出超配資產，順便回歸目標配置
2. **📉 節稅**（Priority 2）：賣出帳面虧損持倉，進行 Tax-Loss Harvesting
3. **💧 流動性**（Priority 3）：按流動性順序（現金 → 債券 → 成長 → 護城河 → 風向球）賣出

#### 使用方式

- 輸入**提款金額**與**幣別**，點擊「💰 計算提款建議」
- 系統會顯示賣出建議表格（標的、數量、金額、原因）與摘要指標（目標金額、可賣出總額、缺口）
- 若投資組合市值不足，會顯示**缺口金額**警告
- 可選擇開啟「📡 發送 Telegram 通知」，將建議同步至 Telegram

> 💡 聰明提款的核心理念：先賣該賣的（超配），再賣能省稅的（虧損），最後才動用流動性高的資產，保護你的複利核心持倉。

---

### Step 6 — 壓力測試（Stress Test）

模擬大盤崩盤情境，檢視你的組合能承受多大衝擊。基於線性 CAPM 模型（β 值）估算各持倉在市場大跌時的預期損失。

- **崩盤情境滑桿**：選擇市場下跌幅度（-50% 到 0%），模擬大盤（如 S&P 500）崩跌時的組合表現
- **組合加權 Beta**：計算整體 Beta 值（Beta > 1.0 表示比大盤波動更大，Beta < 1.0 較穩健）
- **預期蒸發金額**：顯示在此情境下組合預期損失的金額與百分比
- **痛苦等級分類**：
  - 🟢 微風輕拂（< 10% 損失）
  - 🟡 有感修正（10-20% 損失）
  - 🟠 傷筋動骨（20-30% 損失）
  - 🔴 睡不著覺（≥ 30% 損失）
- **持倉明細表**：各標的預期損失明細，按影響程度排序
- **智能建議**：達到「睡不著覺」等級時，系統提供風險管理建議（檢視 Beta、緊急備用金、槓桿風險等）
- **隱私模式**：支援金額隱藏，僅顯示百分比與等級

#### 使用方式

- 使用滑桿調整崩盤情境（預設 -20%，建議測試 -30% 和 -50% 極端情境）
- 檢視組合整體 Beta 與預期損失金額
- 查看各持倉明細，找出高風險標的（高 Beta 且占比大）
- 根據痛苦等級與建議，考慮調整持倉結構（增持現金/債券、減碼高 Beta 標的）

> 💡 壓力測試幫助你評估組合抗跌能力，提前了解極端市場情境下的風險暴露。定期檢視 Beta 值與損失預期，是風險管理的重要環節。

---

### Telegram 通知設定（雙模式）

- **系統預設 Bot**：使用 `.env` 中的 `TELEGRAM_BOT_TOKEN`，無需額外設定
- **自訂 Bot**：輸入自訂 Bot Token 與 Chat ID，開啟「使用自訂 Bot」開關
- 啟用自訂 Bot 後，所有掃描通知、價格警報、每週摘要都會透過自訂 Bot 發送
- 未設定或關閉自訂 Bot 時，自動回退使用系統預設 Bot
- **測試按鈕**：儲存設定後可點擊「📨 發送測試訊息」驗證設定是否正確
- **每週摘要**：點擊「📬 發送每週摘要」可手動觸發每週投資組合健康報告（背景執行，結果透過 Telegram 發送）
""")


# ---------------------------------------------------------------------------
# Sidebar: 新增持倉 + 匯出 / 匯入
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("💰 資產管理")
    st.subheader("➕ 新增持倉")

    asset_type = st.radio(
        "資產類型",
        ["📈 股票", "🛡️ 債券", "💵 現金"],
        horizontal=True,
        key="sidebar_asset_type",
    )

    # ---- Stock holding form ----
    if asset_type == "📈 股票":
        sb_market = st.selectbox(
            "市場",
            options=_MARKET_KEYS,
            format_func=_market_label,
            key="sb_stock_market",
        )
        market_info = STOCK_MARKET_OPTIONS[sb_market]
        st.caption(f"幣別：{market_info['currency']}")

        # Ticker outside form for reactive radar lookup
        sb_ticker = st.text_input(
            "股票代號",
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
                    f"📋 已在雷達中，自動同步分類："
                    f"{CATEGORY_LABELS.get(radar_cat, radar_cat)}"
                )
            else:
                st.caption("📌 此股票尚未在雷達中，新增後將自動加入追蹤。")

        # Compute default category index
        default_cat_idx = 0
        if is_in_radar and radar_cat in STOCK_CATEGORY_OPTIONS:
            default_cat_idx = STOCK_CATEGORY_OPTIONS.index(radar_cat)

        # Optional thesis (only for new stocks)
        sb_thesis = ""
        if sb_ticker.strip() and not is_in_radar:
            sb_thesis = st.text_area(
                "投資觀點（選填）",
                placeholder="新增至雷達時的初始觀點...",
                key="sb_stock_thesis",
            )

        with st.form("sidebar_stock_form", clear_on_submit=True):
            sb_cat = st.selectbox(
                "分類",
                options=STOCK_CATEGORY_OPTIONS,
                format_func=lambda x: CATEGORY_LABELS.get(x, x),
                index=default_cat_idx,
                disabled=is_in_radar,
            )
            sb_qty = st.number_input(
                "股數", min_value=0.0, step=1.0, value=0.0
            )
            sb_cost = st.number_input(
                "平均成本", min_value=0.0, step=0.01, value=0.0
            )
            sb_broker = st.text_input(
                "券商（選填）",
                placeholder="例如 永豐金、Firstrade",
                key="sb_stock_broker",
            )

            if st.form_submit_button("新增"):
                if not sb_ticker.strip():
                    st.warning("⚠️ 請輸入股票代號。")
                elif sb_qty <= 0:
                    st.warning("⚠️ 請輸入股數。")
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
                        st.success(f"✅ 已新增 {full_ticker}")
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
                                st.info("📡 已自動加入雷達追蹤")
                                invalidate_stock_caches()
                        invalidate_holding_caches()
                        refresh_ui()

    # ---- Bond holding form ----
    elif asset_type == "🛡️ 債券":
        # Ticker outside form for reactive radar lookup
        sb_bond_ticker = st.text_input(
            "債券代號",
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
                st.info("📋 已在雷達中，將沿用既有分類。")
            else:
                st.caption("📌 此債券尚未在雷達中，新增後將自動加入追蹤。")

        # Optional thesis (only for new bonds)
        sb_bond_thesis = ""
        if sb_bond_ticker.strip() and not bond_in_radar:
            sb_bond_thesis = st.text_area(
                "投資觀點（選填）",
                placeholder="新增至雷達時的初始觀點...",
                key="sb_bond_thesis",
            )

        with st.form("sidebar_bond_form", clear_on_submit=True):
            sb_bond_currency = st.selectbox(
                "幣別", options=CASH_CURRENCY_OPTIONS
            )
            sb_bond_qty = st.number_input(
                "股數", min_value=0.0, step=1.0, value=0.0, key="sb_bqty"
            )
            sb_bond_cost = st.number_input(
                "平均成本",
                min_value=0.0,
                step=0.01,
                value=0.0,
                key="sb_bcost",
            )
            sb_bond_broker = st.text_input(
                "券商（選填）",
                placeholder="例如 永豐金、Firstrade",
                key="sb_bond_broker",
            )

            if st.form_submit_button("新增"):
                if not sb_bond_ticker.strip():
                    st.warning("⚠️ 請輸入債券代號。")
                elif sb_bond_qty <= 0:
                    st.warning("⚠️ 請輸入股數。")
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
                        st.success(f"✅ 已新增 {bond_full}")
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
                                st.info("📡 已自動加入雷達追蹤")
                                invalidate_stock_caches()
                        invalidate_holding_caches()
                        refresh_ui()

    # ---- Cash holding form ----
    else:
        with st.form("sidebar_cash_form", clear_on_submit=True):
            cash_currency = st.selectbox(
                "幣別", options=CASH_CURRENCY_OPTIONS
            )
            cash_amount = st.number_input(
                "金額", min_value=0.0, step=100.0, value=0.0
            )
            cash_bank = st.text_input(
                "銀行 / 券商（選填）",
                placeholder="例如 台灣銀行、中信銀行",
            )
            cash_account_type = st.selectbox(
                "帳戶類型（選填）",
                options=["（不指定）"] + CASH_ACCOUNT_TYPE_OPTIONS,
            )
            cash_notes = st.text_area(
                "備註（選填）",
                placeholder="例如 緊急預備金、旅遊基金...",
            )

            if st.form_submit_button("新增"):
                if cash_amount <= 0:
                    st.warning("⚠️ 請輸入金額。")
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
                                if cash_account_type != "（不指定）"
                                else None
                            ),
                        },
                    )
                    if result:
                        label_parts = [cash_currency]
                        if cash_bank.strip():
                            label_parts.append(cash_bank.strip())
                        st.success(
                            f"✅ 已新增 {' - '.join(label_parts)}"
                            f" {cash_amount:,.0f}"
                        )
                        invalidate_holding_caches()
                        refresh_ui()

    st.divider()

    # -- Export Holdings --
    st.subheader("📥 匯出持倉")
    export_h = api_get_silent("/holdings/export")
    if export_h:
        st.download_button(
            "📥 下載 JSON",
            data=json.dumps(export_h, ensure_ascii=False, indent=2),
            file_name=HOLDINGS_EXPORT_FILENAME,
            mime="application/json",
            use_container_width=True,
        )
        st.caption(f"共 {len(export_h)} 筆持倉")
    else:
        st.caption("目前無持倉可匯出。")

    st.divider()

    # -- Import Holdings --
    st.subheader("📤 匯入持倉")
    h_file = st.file_uploader(
        "上傳 JSON 檔案",
        type=["json"],
        key="import_holdings_file",
        label_visibility="collapsed",
    )
    if h_file is not None:
        try:
            h_data = json.loads(h_file.getvalue().decode("utf-8"))
            if isinstance(h_data, list):
                st.caption(f"偵測到 {len(h_data)} 筆資料。")
                if st.button("📤 確認匯入", use_container_width=True):
                    result = api_post("/holdings/import", h_data)
                    if result:
                        st.success(
                            result.get("message", "✅ 匯入完成")
                        )
                        invalidate_holding_caches()
                        st.rerun()
            else:
                st.warning("⚠️ JSON 格式錯誤，預期為陣列。")
        except json.JSONDecodeError:
            st.error("❌ 無法解析 JSON 檔案。")

    st.download_button(
        "📋 下載匯入範本",
        data=HOLDING_IMPORT_TEMPLATE,
        file_name="holding_import_template.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()

    # -- Refresh --
    if st.button("🔄 重新整理畫面", use_container_width=True):
        invalidate_all_caches()
        refresh_ui()


# ---------------------------------------------------------------------------
# Main Content: Tabs (War Room + Telegram)
# ---------------------------------------------------------------------------

tab_warroom, tab_telegram = st.tabs(
    ["📊 資產配置 War Room", "📡 Telegram 設定"]
)


# ===========================================================================
# Tab 1: War Room — Asset Allocation Dashboard
# ===========================================================================

with tab_warroom:
    try:
        templates = fetch_templates() or []
        profile = fetch_profile()
        holdings = fetch_holdings() or []

        # Step 1: Target Allocation
        render_target(templates, profile, holdings)

        st.divider()

        # Step 2: Holdings Management
        render_holdings(holdings)

        st.divider()

        # Steps 3-5: Analysis (require profile + holdings)
        if profile and holdings:
            display_cur = "USD"
            render_rebalance(profile, holdings, default_currency=display_cur)
            st.divider()
            render_currency_exposure(profile, holdings, display_cur)
            st.divider()
            render_withdrawal(profile, holdings)
        elif not profile:
            st.caption("請先完成 Step 1（設定目標配置）。")
        else:
            st.caption("請先完成 Step 2（輸入持倉）。")

        # Step 6: Stress Test
        st.divider()
        if holdings:
            # Read display_cur from rebalance selectbox (session_state)
            stress_display_cur = st.session_state.get(
                "display_currency", "USD"
            )
            render_stress_test(display_currency=stress_display_cur)
        else:
            st.subheader("📊 Step 6 — 壓力測試")
            st.info("請先在 Step 2 新增持倉，才能進行壓力測試。")

    except Exception as e:
        st.error(f"❌ 資產配置載入失敗：{e}")


# ===========================================================================
# Tab 2: Telegram Settings
# ===========================================================================

with tab_telegram:
    st.subheader("🔔 Telegram 通知設定")
    st.caption(
        "系統支援兩種模式：使用系統預設 Bot（.env 設定）或自訂 Bot Token。"
    )

    tg_settings = api_get_silent("/settings/telegram")

    if tg_settings:
        mode_label = (
            "🟢 自訂 Bot"
            if tg_settings.get("use_custom_bot")
            else "⚪ 系統預設"
        )
        tg_cols = st.columns(3)
        with tg_cols[0]:
            st.metric("模式", mode_label)
        with tg_cols[1]:
            st.metric(
                "Chat ID",
                tg_settings.get("telegram_chat_id") or "未設定",
            )
        with tg_cols[2]:
            st.metric(
                "自訂 Token",
                tg_settings.get("custom_bot_token_masked") or "未設定",
            )

    with st.expander(
        "✏️ 編輯 Telegram 設定",
        expanded=not bool(
            tg_settings and tg_settings.get("telegram_chat_id")
        ),
    ):
        with st.form("telegram_settings_form"):
            tg_chat = st.text_input(
                "Telegram Chat ID",
                value=(tg_settings or {}).get("telegram_chat_id", ""),
                placeholder="例如 123456789",
            )
            tg_token = st.text_input(
                "自訂 Bot Token（選填）",
                value="",
                placeholder="留空則保留原有設定",
                type="password",
            )
            tg_custom = st.toggle(
                "使用自訂 Bot",
                value=(tg_settings or {}).get("use_custom_bot", False),
            )
            st.caption(
                "💡 若未設定自訂 Bot，系統會使用 `.env` 中的"
                " `TELEGRAM_BOT_TOKEN` 發送通知。"
                "自訂 Bot 適用於想要分開管理通知頻道的使用者。"
            )

            if st.form_submit_button("💾 儲存設定"):
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
            if st.button("📨 發送測試訊息", key="test_telegram_btn"):
                level, msg = post_telegram_test()
                show_toast(level, msg)
        with btn_cols[1]:
            if st.button("📬 發送每週摘要", key="trigger_digest_btn"):
                level, msg = post_digest()
                show_toast(level, msg)

    # -------------------------------------------------------------------
    # Notification Preferences — selective alert toggles
    # -------------------------------------------------------------------
    st.divider()
    st.subheader("🔕 通知偏好")
    st.caption("選擇要接收哪些類型的 Telegram 通知。停用的通知仍會在系統中執行，但不會發送訊息。")

    _NOTIF_LABELS: dict[str, tuple[str, str]] = {
        "scan_alerts": ("🔔 掃描訊號通知", "THESIS_BROKEN / OVERHEATED / CONTRARIAN_BUY 等掃描結果變化"),
        "price_alerts": ("⚡ 自訂價格警報", "當股價突破你設定的門檻時觸發"),
        "weekly_digest": ("📊 每週投資摘要", "每週一次的投資組合健康分數與訊號彙整"),
        "xray_alerts": ("🔬 X-Ray 集中度警告", "穿透式持倉分析發現集中度過高時"),
        "fx_alerts": ("💱 匯率曝險警報", "匯率風險等級異常或匯率大幅波動時"),
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

        if st.form_submit_button("💾 儲存通知偏好"):
            level, msg = put_notification_preferences(current_privacy, new_prefs)
            show_toast(level, msg)
            if level == "success":
                fetch_preferences.clear()
                st.rerun()
