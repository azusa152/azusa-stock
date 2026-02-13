"""
Folio — Asset Allocation Page (個人資產配置).
Holdings management, rebalancing, and Telegram settings.
"""

import json
import re

import pandas as pd
import requests
import streamlit as st

from collections import defaultdict

from config import (
    ALLOCATION_CHART_HEIGHT,
    API_POST_TIMEOUT,
    API_PUT_TIMEOUT,
    BACKEND_URL,
    CASH_ACCOUNT_TYPE_OPTIONS,
    CASH_CURRENCY_OPTIONS,
    CATEGORY_COLOR_FALLBACK,
    CATEGORY_COLOR_MAP,
    CATEGORY_ICON_SHORT,
    CATEGORY_LABELS,
    CATEGORY_OPTIONS,
    DISPLAY_CURRENCY_OPTIONS,
    DRIFT_CHART_HEIGHT,
    HOLDING_IMPORT_TEMPLATE,
    HOLDINGS_EXPORT_FILENAME,
    PRIVACY_MASK,
    PRIVACY_TOGGLE_LABEL,
    STOCK_CATEGORY_OPTIONS,
    STOCK_MARKET_OPTIONS,
    STOCK_MARKET_PLACEHOLDERS,
    XRAY_TOP_N_DISPLAY,
    XRAY_WARN_THRESHOLD_PCT,
)
from utils import (
    api_delete,
    api_get_silent,
    api_post,
    api_put,
    build_radar_lookup,
    fetch_currency_exposure,
    fetch_holdings,
    fetch_preferences,
    fetch_profile,
    fetch_rebalance,
    fetch_templates,
    format_utc_timestamp,
    invalidate_all_caches,
    invalidate_holding_caches,
    invalidate_profile_caches,
    invalidate_stock_caches,
    is_privacy as _is_privacy,
    mask_money as _mask_money,
    mask_qty as _mask_qty,
    on_privacy_change as _on_privacy_change,
    refresh_ui,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MARKET_KEYS = list(STOCK_MARKET_OPTIONS.keys())


def _hex_to_rgb_str(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'rgb(r, g, b)' for plotly.colors.n_colors."""
    h = hex_color.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


def _market_label(key: str) -> str:
    return STOCK_MARKET_OPTIONS[key]["label"]


# Regex: match numeric amounts (e.g. "50,000", "1,234.56") followed by a currency code
_CURRENCY_AMOUNT_RE = re.compile(
    r"[\d,]+(?:\.\d+)?(?=\s*(?:TWD|USD|JPY|EUR|GBP|CNY|HKD|SGD|THB))"
)


def _render_advice(advice_lines: list[str]) -> None:
    """Render advice lines, masking monetary amounts in privacy mode."""
    for adv in advice_lines:
        if _is_privacy():
            masked = _CURRENCY_AMOUNT_RE.sub(PRIVACY_MASK, adv)
            st.write(masked)
        else:
            st.write(adv)


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

### Telegram 通知設定（雙模式）

- **系統預設 Bot**：使用 `.env` 中的 `TELEGRAM_BOT_TOKEN`，無需額外設定
- **自訂 Bot**：輸入自訂 Bot Token 與 Chat ID，開啟「使用自訂 Bot」開關
- 啟用自訂 Bot 後，所有掃描通知、價格警報、每週摘要都會透過自訂 Bot 發送
- 未設定或關閉自訂 Bot 時，自動回退使用系統預設 Bot
- **測試按鈕**：儲存設定後可點擊「📨 發送測試訊息」驗證設定是否正確
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

        # -------------------------------------------------------------------
        # Section 1: Target Allocation
        # -------------------------------------------------------------------
        st.subheader("🎯 Step 1 — 設定目標配置")

        if profile:
            prof_cols = st.columns([5, 1])
            with prof_cols[0]:
                home_cur = profile.get("home_currency", "TWD")
                st.success(
                    f"✅ 目前使用配置：**{profile['name']}** ｜ 🏠 本幣：{home_cur}"
                )
            with prof_cols[1]:
                switch_clicked = st.button(
                    "🔄 切換風格", key="switch_persona_btn"
                )

            target = profile.get("config", {})

            target_cols = st.columns(len(CATEGORY_OPTIONS))
            for i, cat in enumerate(CATEGORY_OPTIONS):
                with target_cols[i]:
                    label = CATEGORY_LABELS.get(cat, cat)
                    pct = target.get(cat, 0)
                    st.metric(label.split(" ")[0], f"{pct}%")

            # -- Switch Persona picker --
            if switch_clicked:
                with st.expander(
                    "🔄 選擇新的投資風格範本", expanded=True
                ):
                    if templates:
                        sw_cols = st.columns(3)
                        for idx, tmpl in enumerate(templates):
                            with sw_cols[idx % 3]:
                                with st.container(border=True):
                                    st.markdown(f"**{tmpl['name']}**")
                                    st.caption(tmpl["description"])
                                    if tmpl.get("quote"):
                                        st.markdown(
                                            f"*「{tmpl['quote']}」*"
                                        )

                                    cfg = tmpl.get("default_config", {})
                                    non_zero = {
                                        k: v
                                        for k, v in cfg.items()
                                        if v > 0
                                    }
                                    if non_zero:
                                        parts = [
                                            f"{CATEGORY_LABELS.get(k, k).split(' ')[0]} {v}%"
                                            for k, v in non_zero.items()
                                        ]
                                        st.caption(" · ".join(parts))

                                    if st.button(
                                        "選擇此範本",
                                        key=f"switch_tmpl_{tmpl['id']}",
                                        use_container_width=True,
                                    ):
                                        result = api_post(
                                            "/profiles",
                                            {
                                                "name": tmpl["name"],
                                                "source_template_id": tmpl[
                                                    "id"
                                                ],
                                                "config": cfg,
                                                "home_currency": profile.get("home_currency", "TWD"),
                                            },
                                        )
                                        if result:
                                            st.success(
                                                f"✅ 已切換至「{tmpl['name']}」"
                                            )
                                            invalidate_profile_caches()
                                            st.rerun()
                    else:
                        st.warning("⚠️ 無法載入範本。")

            # -- Adjust percentages --
            with st.expander("✏️ 調整目標配置", expanded=False):
                edit_cols = st.columns(len(CATEGORY_OPTIONS))
                new_config = {}
                for i, cat in enumerate(CATEGORY_OPTIONS):
                    with edit_cols[i]:
                        label = (
                            CATEGORY_LABELS.get(cat, cat)
                            .split("(")[0]
                            .strip()
                        )
                        new_config[cat] = st.number_input(
                            label,
                            min_value=0.0,
                            max_value=100.0,
                            value=float(target.get(cat, 0)),
                            step=5.0,
                            key=f"target_{cat}",
                        )

                total_pct = sum(new_config.values())
                if abs(total_pct - 100) > 0.01:
                    st.warning(
                        f"⚠️ 配置合計 {total_pct:.0f}%，應為 100%。"
                    )
                else:
                    if st.button("💾 儲存配置", key="save_profile"):
                        result = api_put(
                            f"/profiles/{profile['id']}",
                            {"config": new_config},
                        )
                        if result:
                            st.success("✅ 配置已更新")
                            invalidate_profile_caches()
                            st.rerun()
        else:
            st.info(
                "📋 尚未設定投資組合目標，請選擇一個投資人格範本開始："
            )

            init_home_cur = st.selectbox(
                "🏠 本幣 (Home Currency)",
                options=DISPLAY_CURRENCY_OPTIONS,
                index=DISPLAY_CURRENCY_OPTIONS.index("TWD") if "TWD" in DISPLAY_CURRENCY_OPTIONS else 0,
                key="init_home_currency",
                help="用於匯率曝險計算的基準幣別。",
            )

            if templates:
                template_cols = st.columns(3)
                for idx, tmpl in enumerate(templates):
                    with template_cols[idx % 3]:
                        with st.container(border=True):
                            st.markdown(f"**{tmpl['name']}**")
                            st.caption(tmpl["description"])
                            if tmpl.get("quote"):
                                st.markdown(f"*「{tmpl['quote']}」*")

                            cfg = tmpl.get("default_config", {})
                            non_zero = {
                                k: v for k, v in cfg.items() if v > 0
                            }
                            if non_zero:
                                parts = [
                                    f"{CATEGORY_LABELS.get(k, k).split(' ')[0]} {v}%"
                                    for k, v in non_zero.items()
                                ]
                                st.caption(" · ".join(parts))

                            if st.button(
                                "選擇此範本",
                                key=f"pick_template_{tmpl['id']}",
                                use_container_width=True,
                            ):
                                result = api_post(
                                    "/profiles",
                                    {
                                        "name": tmpl["name"],
                                        "source_template_id": tmpl["id"],
                                        "config": cfg,
                                        "home_currency": init_home_cur,
                                    },
                                )
                                if result:
                                    st.success(
                                        f"✅ 已套用「{tmpl['name']}」"
                                    )
                                    invalidate_profile_caches()
                                    st.rerun()
            else:
                st.warning("⚠️ 無法載入範本，請確認後端服務。")

        st.divider()

        # -------------------------------------------------------------------
        # Section 2: Holdings Management (inline editor + save + delete)
        # -------------------------------------------------------------------
        st.subheader("💼 Step 2 — 持倉管理")

        if holdings:
            # Build DataFrame with raw API values for round-trip editing
            rows = []
            for h in holdings:
                is_cash = h.get("is_cash", False)
                rows.append(
                    {
                        "ID": h["id"],
                        "ticker": (
                            "" if is_cash else h["ticker"]
                        ),
                        "raw_ticker": h["ticker"],
                        "category": h["category"],
                        "quantity": float(h["quantity"]),
                        "cost_basis": (
                            float(h["cost_basis"])
                            if h.get("cost_basis") is not None
                            else None
                        ),
                        "broker": h.get("broker") or "",
                        "currency": h.get("currency", "USD"),
                        "account_type": h.get("account_type") or "",
                        "is_cash": is_cash,
                    }
                )
            df = pd.DataFrame(rows)

            if _is_privacy():
                # Privacy mode: show masked read-only table
                masked_df = df.copy()
                masked_df["quantity"] = PRIVACY_MASK
                masked_df["cost_basis"] = PRIVACY_MASK
                st.dataframe(
                    masked_df.drop(columns=["ID", "raw_ticker"]),
                    column_config={
                        "ticker": "代號",
                        "category": "分類",
                        "quantity": "數量",
                        "cost_basis": "平均成本",
                        "broker": "銀行/券商",
                        "currency": "幣別",
                        "account_type": "帳戶類型",
                        "is_cash": "現金",
                    },
                    use_container_width=True,
                    hide_index=True,
                )
                edited_df = df  # no edits in privacy mode
                st.caption("🔒 隱私模式已開啟，關閉後可編輯持倉。")
            else:
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "ID": None,  # hidden
                        "raw_ticker": None,  # hidden
                        "ticker": st.column_config.TextColumn(
                            "代號", disabled=True
                        ),
                        "category": st.column_config.SelectboxColumn(
                            "分類",
                            options=CATEGORY_OPTIONS,
                            required=True,
                        ),
                        "quantity": st.column_config.NumberColumn(
                            "數量", min_value=0.0, format="%.4f"
                        ),
                        "cost_basis": st.column_config.NumberColumn(
                            "平均成本", min_value=0.0, format="%.2f"
                        ),
                        "broker": st.column_config.TextColumn(
                            "銀行/券商"
                        ),
                        "currency": st.column_config.TextColumn(
                            "幣別", disabled=True
                        ),
                        "account_type": st.column_config.TextColumn(
                            "帳戶類型"
                        ),
                        "is_cash": st.column_config.CheckboxColumn(
                            "現金", disabled=True
                        ),
                    },
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    key="holdings_editor",
                )

            # --- Save button ---
            save_clicked = st.button(
                "💾 儲存變更",
                key="save_holdings_btn",
                disabled=_is_privacy(),
            )

            # --- Save logic: diff edited vs original ---
            if save_clicked:
                changed = 0
                errors: list[str] = []
                for idx in range(len(df)):
                    orig = df.iloc[idx]
                    edit = edited_df.iloc[idx]
                    # Check if any editable field changed
                    if (
                        orig["category"] != edit["category"]
                        or orig["quantity"] != edit["quantity"]
                        or orig["cost_basis"] != edit["cost_basis"]
                        or (orig["broker"] or "")
                        != (edit["broker"] or "")
                        or (orig["account_type"] or "")
                        != (edit["account_type"] or "")
                    ):
                        h_id = int(orig["ID"])
                        result = api_put(
                            f"/holdings/{h_id}",
                            {
                                "ticker": orig["raw_ticker"],
                                "category": edit["category"],
                                "quantity": float(edit["quantity"]),
                                "cost_basis": (
                                    float(edit["cost_basis"])
                                    if pd.notna(edit["cost_basis"])
                                    else None
                                ),
                                "broker": (
                                    edit["broker"]
                                    if edit["broker"]
                                    else None
                                ),
                                "currency": edit.get(
                                    "currency", "USD"
                                ),
                                "account_type": (
                                    edit["account_type"]
                                    if edit["account_type"]
                                    else None
                                ),
                                "is_cash": bool(edit["is_cash"]),
                            },
                        )
                        if result:
                            changed += 1
                        else:
                            errors.append(
                                orig["raw_ticker"]
                            )
                if changed > 0:
                    st.success(f"✅ 已更新 {changed} 筆持倉")
                if errors:
                    st.error(
                        f"❌ 更新失敗：{', '.join(errors)}"
                    )
                if changed == 0 and not errors:
                    st.info("ℹ️ 沒有偵測到變更")
                if changed > 0:
                    invalidate_holding_caches()
                    st.rerun()

            # --- Delete logic: selector first, then button ---
            st.divider()
            del_cols = st.columns([3, 1])
            with del_cols[0]:
                _priv = _is_privacy()
                del_id = st.selectbox(
                    "選擇要刪除的持倉",
                    options=[h["id"] for h in holdings],
                    format_func=lambda x: next(
                        (
                            (
                                h["ticker"]
                                if _priv
                                else f"{h['ticker']} ({h['quantity']})"
                            )
                            for h in holdings
                            if h["id"] == x
                        ),
                        str(x),
                    ),
                    key="del_holding_id",
                )
            with del_cols[1]:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(
                    "🗑️ 刪除", key="del_holding_btn"
                ):
                    result = api_delete(f"/holdings/{del_id}")
                    if result:
                        st.success(
                            result.get("message", "✅ 已刪除")
                        )
                        invalidate_holding_caches()
                        st.rerun()
        else:
            st.caption(
                "目前無持倉資料，請透過左側面板新增股票、債券或現金。"
            )

        st.divider()

        # -------------------------------------------------------------------
        # Section 3: Rebalance Analysis
        # -------------------------------------------------------------------
        st.subheader("📊 Step 3 — 再平衡分析")

        if profile and holdings:
            # Currency selector
            cur_cols = st.columns([2, 2, 2])
            with cur_cols[0]:
                display_cur = st.selectbox(
                    "顯示幣別",
                    options=DISPLAY_CURRENCY_OPTIONS,
                    index=0,
                    key="display_currency",
                )
            with cur_cols[1]:
                st.write("")  # vertical spacer
                _do_load = st.button(
                    "📊 載入再平衡分析",
                    type="primary",
                    key="btn_load_rebalance",
                )
            # Persist loaded state so currency change doesn't lose data
            if _do_load:
                st.session_state["rebalance_loaded"] = True

            rebalance = None
            if st.session_state.get("rebalance_loaded"):
                with st.status("📊 載入再平衡分析中...", expanded=True) as _rb_status:
                    rebalance = fetch_rebalance(display_currency=display_cur)
                    if rebalance:
                        _rb_status.update(
                            label="✅ 再平衡分析載入完成",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        _rb_status.update(
                            label="⚠️ 載入失敗或無持倉資料",
                            state="error",
                            expanded=True,
                        )
            else:
                st.info("💡 點擊上方「載入再平衡分析」按鈕以取得最新資料。")
            if rebalance:
                calc_at = rebalance.get("calculated_at", "")
                if calc_at:
                    with cur_cols[1]:
                        browser_tz = st.session_state.get("browser_tz")
                        st.caption(
                            f"🕐 資料更新時間：{format_utc_timestamp(calc_at, browser_tz)}"
                        )
                st.metric(
                    f"💰 投資組合總市值（{display_cur}）",
                    _mask_money(rebalance["total_value"]),
                )

                import plotly.graph_objects as go
                from plotly.subplots import make_subplots

                cats_data = rebalance.get("categories", {})
                cat_names = list(cats_data.keys())
                cat_labels = [
                    CATEGORY_LABELS.get(c, c).split("(")[0].strip()
                    for c in cat_names
                ]
                total_val = rebalance["total_value"]

                # --- Target Pie: category + target dollar amount ---
                target_amounts = [
                    round(
                        total_val
                        * cats_data[c]["target_pct"]
                        / 100,
                        2,
                    )
                    for c in cat_names
                ]
                target_text = [
                    _mask_money(amt, "${:,.0f}")
                    for amt in target_amounts
                ]

                # --- Actual Pie: per-stock breakdown (grouped by category color) ---
                import plotly.colors as pc

                detail = rebalance.get("holdings_detail", [])
                cat_groups: dict[str, list] = defaultdict(list)
                for d in detail:
                    cat_groups[d["category"]].append(d)

                actual_labels = []
                actual_values = []
                actual_text = []
                actual_colors = []
                for cat, items in cat_groups.items():
                    base = CATEGORY_COLOR_MAP.get(cat, CATEGORY_COLOR_FALLBACK)
                    icon = CATEGORY_ICON_SHORT.get(cat, "")
                    n = len(items)
                    if n == 1:
                        shades = [base]
                    else:
                        shades = pc.n_colors(
                            _hex_to_rgb_str(base),
                            "rgb(255, 255, 255)",
                            n + 2,
                            colortype="rgb",
                        )[:-2]
                    for i, d in enumerate(items):
                        actual_labels.append(f"{icon} {d['ticker']}")
                        actual_values.append(d["market_value"])
                        actual_text.append(
                            _mask_money(d["market_value"], "${:,.0f}")
                        )
                        actual_colors.append(shades[i])

                fig_pie = make_subplots(
                    rows=1,
                    cols=2,
                    specs=[[{"type": "pie"}, {"type": "pie"}]],
                    subplot_titles=[
                        f"🎯 目標配置（{display_cur}）",
                        f"📊 實際配置（{display_cur}）",
                    ],
                )

                # Target pie — categories with matching base colors
                target_colors = [
                    CATEGORY_COLOR_MAP.get(c, CATEGORY_COLOR_FALLBACK)
                    for c in cat_names
                ]
                _privacy = _is_privacy()
                fig_pie.add_trace(
                    go.Pie(
                        labels=cat_labels,
                        values=target_amounts,
                        hole=0.4,
                        text=target_text,
                        textinfo=(
                            "label+percent"
                            if _privacy
                            else "label+text+percent"
                        ),
                        textposition="auto",
                        marker=dict(colors=target_colors),
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "佔比：%{percent}<extra></extra>"
                            if _privacy
                            else (
                                "<b>%{label}</b><br>"
                                f"目標金額：%{{text}} {display_cur}<br>"
                                "佔比：%{percent}<extra></extra>"
                            )
                        ),
                    ),
                    row=1,
                    col=1,
                )

                # Actual pie — individual stocks with category-colored shades
                fig_pie.add_trace(
                    go.Pie(
                        labels=actual_labels,
                        values=actual_values,
                        hole=0.4,
                        text=actual_text,
                        textinfo=(
                            "label+percent"
                            if _privacy
                            else "label+text+percent"
                        ),
                        textposition="auto",
                        marker=dict(colors=actual_colors),
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "佔比：%{percent}<extra></extra>"
                            if _privacy
                            else (
                                "<b>%{label}</b><br>"
                                f"市值：%{{text}} {display_cur}<br>"
                                "佔比：%{percent}<extra></extra>"
                            )
                        ),
                    ),
                    row=1,
                    col=2,
                )

                fig_pie.update_layout(
                    height=ALLOCATION_CHART_HEIGHT,
                    margin=dict(t=40, b=20, l=20, r=20),
                    showlegend=False,
                )
                st.plotly_chart(fig_pie, use_container_width=True)

                # Drift chart
                drift_vals = [
                    cats_data[c]["drift_pct"] for c in cat_names
                ]
                colors = [
                    "#ef4444" if d > 0 else "#22c55e" for d in drift_vals
                ]
                fig_drift = go.Figure(
                    go.Bar(
                        x=cat_labels,
                        y=drift_vals,
                        marker_color=colors,
                        text=[f"{d:+.1f}%" for d in drift_vals],
                        textposition="outside",
                    )
                )
                fig_drift.update_layout(
                    title="偏移度 (Drift %)",
                    yaxis_title="偏移 (%)",
                    height=DRIFT_CHART_HEIGHT,
                    margin=dict(t=40, b=20, l=40, r=20),
                )
                st.plotly_chart(fig_drift, use_container_width=True)

                # Advice
                st.markdown("**💡 再平衡建議：**")
                for adv in rebalance.get("advice", []):
                    st.write(adv)

                # Holdings breakdown (merged by ticker)
                detail = rebalance.get("holdings_detail", [])
                if detail:
                    st.divider()
                    st.markdown(
                        f"**📋 個股持倉明細（{display_cur}）：**"
                    )
                    detail_rows = []
                    for d in detail:
                        cat_lbl = (
                            CATEGORY_LABELS.get(
                                d["category"], d["category"]
                            )
                            .split("(")[0]
                            .strip()
                        )
                        orig_cur = d.get("currency", "USD")

                        # 計算未實現損益
                        cur_price = d.get("current_price")
                        avg_cost = d.get("avg_cost")
                        qty = d.get("quantity", 0)
                        fx = d.get("fx", 1.0)

                        pl_value = None
                        pl_pct = None
                        if (
                            cur_price is not None
                            and avg_cost is not None
                            and avg_cost > 0
                        ):
                            pl_value = (cur_price - avg_cost) * qty * fx
                            pl_pct = ((cur_price - avg_cost) / avg_cost) * 100

                        # 格式化 P/L 顯示
                        if _is_privacy():
                            pl_display = PRIVACY_MASK
                            pl_pct_display = PRIVACY_MASK
                        elif pl_value is not None:
                            sign = "+" if pl_value >= 0 else ""
                            pl_display = f"{sign}${pl_value:,.2f}"
                            pl_pct_display = f"{sign}{pl_pct:.2f}%"
                        else:
                            pl_display = "—"
                            pl_pct_display = "—"

                        detail_rows.append(
                            {
                                "代號": d["ticker"],
                                "分類": cat_lbl,
                                "原幣": orig_cur,
                                "數量": (
                                    _mask_qty(d["quantity"])
                                ),
                                "現價": (
                                    _mask_money(
                                        d["current_price"]
                                    )
                                    if d.get("current_price")
                                    else "—"
                                ),
                                "平均成本": (
                                    _mask_money(d["avg_cost"])
                                    if d.get("avg_cost")
                                    else "—"
                                ),
                                f"市值({display_cur})": (
                                    _mask_money(
                                        d["market_value"]
                                    )
                                ),
                                "未實現損益": pl_display,
                                "損益%": pl_pct_display,
                                "佔比": f"{d['weight_pct']:.1f}%",
                            }
                        )
                    detail_df = pd.DataFrame(detail_rows)
                    st.dataframe(
                        detail_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                # ----- X-Ray: Portfolio Overlap Analysis -----
                xray = rebalance.get("xray", [])
                if xray:
                    st.divider()
                    st.markdown(
                        f"**🔬 穿透式持倉 X-Ray（{display_cur}）：**"
                    )
                    st.caption(
                        "解析 ETF 成分股，揭示直接持倉與 ETF 間接曝險的真實比例。"
                    )

                    # -- Warning callouts --
                    for entry in xray:
                        if (
                            entry["total_weight_pct"]
                            > XRAY_WARN_THRESHOLD_PCT
                            and entry["indirect_value"] > 0
                        ):
                            sources = ", ".join(
                                entry.get("indirect_sources", [])
                            )
                            st.warning(
                                f"⚠️ **{entry['symbol']}** 直接持倉佔 "
                                f"{entry['direct_weight_pct']:.1f}%，"
                                f"加上 ETF 間接曝險（{sources}），"
                                f"真實曝險已達 "
                                f"**{entry['total_weight_pct']:.1f}%**，"
                                f"超過建議值 "
                                f"{XRAY_WARN_THRESHOLD_PCT:.0f}%。"
                            )

                    # -- Stacked bar chart (top N) --
                    top_xray = xray[:XRAY_TOP_N_DISPLAY]
                    xray_symbols = [
                        e["symbol"] for e in reversed(top_xray)
                    ]
                    xray_direct = [
                        e["direct_weight_pct"]
                        for e in reversed(top_xray)
                    ]
                    xray_indirect = [
                        e["indirect_weight_pct"]
                        for e in reversed(top_xray)
                    ]

                    fig_xray = go.Figure()
                    fig_xray.add_trace(
                        go.Bar(
                            y=xray_symbols,
                            x=xray_direct,
                            name="直接持倉",
                            orientation="h",
                            marker_color="#4A90D9",
                            text=[
                                f"{v:.1f}%" if v > 0.5 else ""
                                for v in xray_direct
                            ],
                            textposition="inside",
                        )
                    )
                    fig_xray.add_trace(
                        go.Bar(
                            y=xray_symbols,
                            x=xray_indirect,
                            name="ETF 間接曝險",
                            orientation="h",
                            marker_color="#F5A623",
                            text=[
                                f"{v:.1f}%" if v > 0.5 else ""
                                for v in xray_indirect
                            ],
                            textposition="inside",
                        )
                    )
                    # Threshold line
                    fig_xray.add_vline(
                        x=XRAY_WARN_THRESHOLD_PCT,
                        line_dash="dash",
                        line_color="red",
                        annotation_text=(
                            f"風險門檻 {XRAY_WARN_THRESHOLD_PCT:.0f}%"
                        ),
                        annotation_position="top right",
                    )
                    fig_xray.update_layout(
                        barmode="stack",
                        height=max(300, len(top_xray) * 28 + 80),
                        margin=dict(t=30, b=20, l=80, r=20),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                        ),
                        xaxis_title=f"佔比 (%)",
                    )
                    st.plotly_chart(
                        fig_xray, use_container_width=True
                    )

                    # -- Summary table --
                    xray_rows = []
                    for e in xray:
                        xray_rows.append(
                            {
                                "標的": e["symbol"],
                                "名稱": e.get("name", ""),
                                "直接 (%)": (
                                    f"{e['direct_weight_pct']:.1f}"
                                ),
                                "間接 (%)": (
                                    f"{e['indirect_weight_pct']:.1f}"
                                ),
                                "真實曝險 (%)": (
                                    f"{e['total_weight_pct']:.1f}"
                                ),
                                f"直接市值({display_cur})": (
                                    _mask_money(
                                        e["direct_value"],
                                        "${:,.0f}",
                                    )
                                ),
                                f"間接市值({display_cur})": (
                                    _mask_money(
                                        e["indirect_value"],
                                        "${:,.0f}",
                                    )
                                ),
                                "間接來源": ", ".join(
                                    e.get("indirect_sources", [])
                                ),
                            }
                        )
                    xray_df = pd.DataFrame(xray_rows)
                    st.dataframe(
                        xray_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    # -- Telegram alert button --
                    if st.button(
                        "📨 發送 X-Ray 警告至 Telegram",
                        key="xray_tg_btn",
                    ):
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/rebalance/xray-alert",
                                params={
                                    "display_currency": display_cur
                                },
                                timeout=API_POST_TIMEOUT,
                            )
                            if resp.ok:
                                data = resp.json()
                                w_count = len(
                                    data.get("warnings", [])
                                )
                                st.success(
                                    f"✅ {data.get('message', f'{w_count} 筆警告已發送')}"
                                )
                            else:
                                st.error(
                                    f"❌ 發送失敗：{resp.text}"
                                )
                        except Exception as ex:
                            st.error(f"❌ 發送失敗：{ex}")

                # -----------------------------------------------------------
                # Section 4: Currency Exposure Monitor
                # -----------------------------------------------------------
                st.divider()
                st.subheader("💱 Step 4 — 匯率曝險監控")

                with st.status("💱 載入匯率曝險分析中...", expanded=True) as _fx_status:
                    fx_data = fetch_currency_exposure()
                    if fx_data:
                        _fx_status.update(
                            label="✅ 匯率曝險分析載入完成",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        _fx_status.update(
                            label="⚠️ 匯率曝險分析載入失敗",
                            state="error",
                            expanded=True,
                        )

                if fx_data:
                    fx_calc_at = fx_data.get("calculated_at", "")
                    fx_home = fx_data.get("home_currency", "TWD")

                    # --- Home currency selector (inline in Step 4) ---
                    _fx_hdr_cols = st.columns([3, 1])
                    with _fx_hdr_cols[0]:
                        if fx_calc_at:
                            browser_tz = st.session_state.get("browser_tz")
                            st.caption(
                                f"🕐 分析時間：{format_utc_timestamp(fx_calc_at, browser_tz)}"
                            )
                    with _fx_hdr_cols[1]:
                        _fx_cur_idx = (
                            DISPLAY_CURRENCY_OPTIONS.index(fx_home)
                            if fx_home in DISPLAY_CURRENCY_OPTIONS
                            else 0
                        )
                        new_fx_home = st.selectbox(
                            "🏠 本幣",
                            options=DISPLAY_CURRENCY_OPTIONS,
                            index=_fx_cur_idx,
                            key="fx_home_currency_selector",
                        )
                        if new_fx_home != fx_home and profile:
                            result = api_put(
                                f"/profiles/{profile['id']}",
                                {"home_currency": new_fx_home},
                            )
                            if result:
                                invalidate_profile_caches()
                                st.rerun()

                    # --- Shared data ---
                    risk_colors = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                    risk_labels_map = {"low": "低風險", "medium": "中風險", "high": "高風險"}
                    fx_movements = fx_data.get("fx_movements", [])

                    _CUR_COLORS = {
                        "USD": "#3B82F6", "TWD": "#10B981", "JPY": "#F59E0B",
                        "EUR": "#8B5CF6", "GBP": "#EF4444", "CNY": "#EC4899",
                        "HKD": "#F97316", "SGD": "#14B8A6", "THB": "#6366F1",
                    }

                    def _render_fx_donut(bd_data: list[dict], title: str, home: str) -> None:
                        """Render a currency breakdown donut chart."""
                        if not bd_data:
                            st.info("暫無資料。")
                            return
                        import plotly.graph_objects as go

                        bd_labels = [b["currency"] for b in bd_data]
                        bd_values = [b["value"] for b in bd_data]
                        bd_text = [_mask_money(b["value"], "${:,.0f}") for b in bd_data]
                        bd_colors = [_CUR_COLORS.get(b["currency"], "#6B7280") for b in bd_data]

                        fig = go.Figure(
                            go.Pie(
                                labels=bd_labels,
                                values=bd_values,
                                hole=0.45,
                                text=bd_text,
                                textinfo=(
                                    "label+percent"
                                    if _is_privacy()
                                    else "label+text+percent"
                                ),
                                textposition="auto",
                                marker=dict(colors=bd_colors),
                                hovertemplate=(
                                    "<b>%{label}</b><br>"
                                    "佔比：%{percent}<extra></extra>"
                                    if _is_privacy()
                                    else (
                                        "<b>%{label}</b><br>"
                                        f"市值：%{{text}} {home}<br>"
                                        "佔比：%{percent}<extra></extra>"
                                    )
                                ),
                            )
                        )
                        fig.update_layout(
                            title=title,
                            height=380,
                            margin=dict(t=40, b=20, l=20, r=20),
                            showlegend=True,
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    def _render_fx_movements(movements: list[dict]) -> None:
                        """Render the FX movements table."""
                        if not movements:
                            return
                        st.markdown("**📉📈 近期匯率變動：**")
                        mv_rows = []
                        for mv in movements:
                            direction_icon = (
                                "📈" if mv["direction"] == "up"
                                else ("📉" if mv["direction"] == "down" else "➡️")
                            )
                            mv_rows.append({
                                "": direction_icon,
                                "貨幣對": mv["pair"],
                                "現價": PRIVACY_MASK if _is_privacy() else f"{mv['current_rate']:.4f}",
                                "變動": f"{mv['change_pct']:+.2f}%",
                            })
                        st.dataframe(
                            pd.DataFrame(mv_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

                    _ALERT_TYPE_BADGES = {
                        "daily_spike": ("🔴", "單日劇烈波動"),
                        "short_term_swing": ("🟡", "短期波段變動"),
                        "long_term_trend": ("🔵", "長期趨勢變動"),
                    }

                    def _render_fx_rate_alerts(rate_alerts: list[dict]) -> None:
                        """Render FX rate change alerts with colored badges."""
                        if not rate_alerts:
                            return
                        st.markdown("**⚡ 匯率變動警報：**")
                        alert_rows = []
                        for a in rate_alerts:
                            badge, label = _ALERT_TYPE_BADGES.get(
                                a["alert_type"], ("⚪", a["alert_type"])
                            )
                            direction_icon = "📈" if a["direction"] == "up" else "📉"
                            alert_rows.append({
                                "": f"{badge} {direction_icon}",
                                "類型": label,
                                "貨幣對": a["pair"],
                                "期間": a["period_label"],
                                "變動": f"{a['change_pct']:+.2f}%",
                                "現價": (
                                    PRIVACY_MASK if _is_privacy()
                                    else f"{a['current_rate']:.4f}"
                                ),
                            })
                        st.dataframe(
                            pd.DataFrame(alert_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # --- Two tabs: Cash vs Total ---
                    fx_tab_cash, fx_tab_total = st.tabs(
                        ["💵 現金幣別曝險", "📊 全資產幣別曝險"]
                    )

                    # === Cash tab ===
                    with fx_tab_cash:
                        cash_bd = fx_data.get("cash_breakdown", [])
                        cash_nhp = fx_data.get("cash_non_home_pct", 0.0)
                        total_cash = fx_data.get("total_cash_home", 0.0)

                        if not cash_bd:
                            st.info("尚無現金部位，請先在 Step 2 輸入現金持倉。")
                        else:
                            # Risk level from backend (based on alert severity)
                            cash_risk = fx_data.get("risk_level", "low")

                            cash_m_cols = st.columns(3)
                            with cash_m_cols[0]:
                                st.metric(
                                    f"💰 現金總額（{fx_home}）",
                                    _mask_money(total_cash),
                                )
                            with cash_m_cols[1]:
                                st.metric("🌍 現金非本幣佔比", f"{cash_nhp:.1f}%")
                            with cash_m_cols[2]:
                                c_icon = risk_colors.get(cash_risk, "⚪")
                                c_label = risk_labels_map.get(cash_risk, cash_risk)
                                st.metric("風險等級", f"{c_icon} {c_label}")

                            _render_fx_donut(
                                cash_bd,
                                f"現金幣別分佈（{fx_home}）",
                                fx_home,
                            )
                            _render_fx_movements(fx_movements)
                            _render_fx_rate_alerts(fx_data.get("fx_rate_alerts", []))

                            # Cash-focused advice
                            advice = fx_data.get("advice", [])
                            cash_advice = [
                                a for a in advice
                                if "現金" in a or "💵" in a
                            ]
                            if cash_advice:
                                st.markdown("**💡 現金幣別建議：**")
                                _render_advice(cash_advice)

                            # Telegram alert button
                            if st.button(
                                "📨 發送匯率曝險警報至 Telegram",
                                key="fx_alert_tg_cash_btn",
                            ):
                                try:
                                    resp = requests.post(
                                        f"{BACKEND_URL}/currency-exposure/alert",
                                        timeout=API_POST_TIMEOUT,
                                    )
                                    if resp.ok:
                                        data = resp.json()
                                        a_count = len(data.get("alerts", []))
                                        st.success(
                                            f"✅ {data.get('message', f'{a_count} 筆警報已發送')}"
                                        )
                                    else:
                                        st.error(f"❌ 發送失敗：{resp.text}")
                                except Exception as ex:
                                    st.error(f"❌ 發送失敗：{ex}")

                    # === Total tab ===
                    with fx_tab_total:
                        all_bd = fx_data.get("breakdown", [])
                        all_nhp = fx_data.get("non_home_pct", 0.0)
                        total_home = fx_data.get("total_value_home", 0.0)
                        risk_level = fx_data.get("risk_level", "low")

                        total_m_cols = st.columns(3)
                        with total_m_cols[0]:
                            st.metric(
                                f"💰 投資組合總市值（{fx_home}）",
                                _mask_money(total_home),
                            )
                        with total_m_cols[1]:
                            st.metric("🌍 非本幣佔比", f"{all_nhp:.1f}%")
                        with total_m_cols[2]:
                            t_icon = risk_colors.get(risk_level, "⚪")
                            t_label = risk_labels_map.get(risk_level, risk_level)
                            st.metric("風險等級", f"{t_icon} {t_label}")

                        _render_fx_donut(
                            all_bd,
                            f"全資產幣別分佈（{fx_home}）",
                            fx_home,
                        )
                        _render_fx_movements(fx_movements)
                        _render_fx_rate_alerts(fx_data.get("fx_rate_alerts", []))

                        # Full advice
                        advice = fx_data.get("advice", [])
                        if advice:
                            st.markdown("**💡 匯率曝險建議：**")
                            _render_advice(advice)

            else:
                st.info(
                    "⏳ 無法計算再平衡，"
                    "請確認已設定目標配置並輸入持倉。"
                )
        elif not profile:
            st.caption("請先完成 Step 1（設定目標配置）。")
        else:
            st.caption("請先完成 Step 2（輸入持倉）。")

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
                try:
                    resp = requests.put(
                        f"{BACKEND_URL}/settings/telegram",
                        json=payload,
                        timeout=API_PUT_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        st.success("✅ Telegram 設定已儲存")
                        st.rerun()
                    else:
                        st.error(f"❌ 儲存失敗：{resp.text}")
                except requests.RequestException as e:
                    st.error(f"❌ 請求失敗：{e}")

    # Test button (outside form)
    if tg_settings and tg_settings.get("telegram_chat_id"):
        if st.button("📨 發送測試訊息", key="test_telegram_btn"):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/settings/telegram/test",
                    timeout=API_POST_TIMEOUT,
                )
                if resp.status_code == 200:
                    st.success(resp.json().get("message", "✅ 已發送"))
                else:
                    detail = (
                        resp.json().get("detail", resp.text)
                        if resp.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else resp.text
                    )
                    st.error(f"❌ {detail}")
            except requests.RequestException as e:
                st.error(f"❌ 請求失敗：{e}")

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
            try:
                resp = requests.put(
                    f"{BACKEND_URL}/settings/preferences",
                    json={
                        "privacy_mode": current_privacy,
                        "notification_preferences": new_prefs,
                    },
                    timeout=API_PUT_TIMEOUT,
                )
                if resp.status_code == 200:
                    st.success("✅ 通知偏好已儲存")
                    fetch_preferences.clear()
                    st.rerun()
                else:
                    st.error(f"❌ 儲存失敗：{resp.text}")
            except requests.RequestException as e:
                st.error(f"❌ 請求失敗：{e}")
