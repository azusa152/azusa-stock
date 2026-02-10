"""
Folio — Radar Page (投資雷達).
Stock tracking, thesis versioning, scanning, and market signals.
"""

import json

import streamlit as st

from config import (
    CASH_CURRENCY_OPTIONS,
    CATEGORY_LABELS,
    CATEGORY_OPTIONS,
    DEFAULT_TAG_OPTIONS,
    EXPORT_FILENAME,
    RADAR_CATEGORY_OPTIONS,
    STOCK_CATEGORY_OPTIONS,
    STOCK_IMPORT_TEMPLATE,
    STOCK_MARKET_OPTIONS,
    STOCK_MARKET_PLACEHOLDERS,
)
from utils import (
    api_get,
    api_get_silent,
    api_post,
    fetch_removed_stocks,
    fetch_stocks,
    fetch_thesis_history,
    refresh_ui,
    render_reorder_section,
    render_stock_card,
    render_thesis_history,
)


# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------

st.title("📡 Folio")
st.caption("智能資產配置 — 追蹤訊號 · 版控觀點 · 自動提醒")

with st.expander("📖 投資雷達：使用說明書", expanded=False):
    st.markdown("""
### 系統總覽

本系統將資產分為**五大類別**，各自對應不同的追蹤邏輯：

| 分類 | 說明 |
|------|------|
| 🌊 **風向球 (Trend Setter)** | 大盤 ETF、巨頭，觀察資金流向與 Capex |
| 🏰 **護城河 (Moat)** | 供應鏈中不可替代的賣鏟子公司 |
| 🚀 **成長夢想 (Growth)** | 高波動、具想像空間的成長股 |
| 🛡️ **債券 (Bond)** | 國債、投資等級債券 ETF（如 TLT, BND, SGOV）|
| 💵 **現金 (Cash)** | 閒置現金（USD, TWD, JPY）— 於「個人資產配置」頁面管理 |

> 💡 系統分為兩大頁面：**投資雷達**（本頁）負責股票追蹤與掃描，**個人資產配置**負責現金管理、持倉記錄與再平衡分析。可透過左側導覽列切換。

---

### 操作流程

---

#### 1. 抬頭看天氣 — 點擊「🚀 執行掃描」

點擊左側面板的掃描按鈕，系統會在**背景**執行 **V2 三層漏斗分析**（並行掃描 4 股，約 30 秒完成）。系統也會每 30 分鐘自動掃描一次。

首先觀察 **Layer 1 市場情緒**：

| 燈號 | 意義 | 建議 |
|------|------|------|
| 🟢 **POSITIVE（晴天）** | 風向球股票穩健，資金面正常 | 適合尋找個股買點 |
| 🔴 **CAUTION（雨天）** | 風向球轉弱（>50% 跌破 60MA），市場風險升高 | 建議縮手觀望或空手 |

掃描結果透過 **Telegram 差異通知**推播 — 只有訊號發生**變化**時才會收到通知，不會重複推播相同訊號。

> 💡 這一步決定你的「倉位水位」，天氣不好就不要出海。

---

#### 2. 檢查護城河 — 展開「🏰 護城河檢測」

每張股票卡片都有「🏰 護城河檢測」展開區，包含：
- **毛利率指標**：最新毛利率 + YoY 變化量（百分點）
- **5 季走勢圖**：折線圖直觀呈現毛利率趨勢
- **五級自動診斷**：
  - 🔴 **Thesis Broken** — 毛利 YoY 衰退超過 2pp，護城河受損，勿接刀
  - 🟢 **錯殺機會** — 股價回檔（乖離率 < -5%）但毛利成長，基本面強勁
  - 🟢 **護城河穩固** — 毛利率 YoY 成長，基本面健康
  - 🟡 **股價偏弱** — 乖離率偏低但護城河數據持平，留意後續季報
  - ⚪ **觀察中** — 護城河數據持平，持續觀察

> 💡 股價下跌不可怕，可怕的是基本面跟著下跌。毛利率是判斷護城河最直接的指標。

---

#### 3. 判斷燈號 — 查看掃描歷史

掃描完成後，系統對每檔股票產生決策訊號。展開「📈 掃描歷史」可查看最近 10 次掃描結果，以及**連續異常次數**提示：

| 燈號 | 觸發條件 | 操作建議 |
|------|----------|----------|
| 🟢 **CONTRARIAN_BUY** | RSI < 35 + 市場情緒正面 + 護城河穩固 | 腳尖試水溫，分批佈局 |
| 🟡 **OVERHEATED** | 乖離率 > 20% | 過熱訊號，請勿追高 |
| 🔴 **THESIS_BROKEN** | 毛利率 YoY 衰退超過 2 個百分點 | 基本面轉差，建議停損出場 |
| ⚪ **NORMAL** | 無異常 | 持續觀察 |

> 💡 「不要跟股票談戀愛」— 當 Thesis Broken 出現時，果斷執行停損。

---

#### 4. 設定價格警報 — 展開「🔔 價格警報」

每張股票卡片的「🔔 價格警報」展開區可以：
- **建立自訂警報**：選擇指標（RSI / 價格 / 乖離率）、條件（< 或 >）、門檻值
- **檢視現有警報**：查看所有已設定的警報及觸發紀錄
- **刪除警報**：不再需要時一鍵移除

觸發時系統透過 **Telegram 即時通知**，每個警報有 **4 小時冷卻期**避免重複推播。

> 💡 善用 RSI < 30 或 Bias < -20% 等條件，讓系統幫你盯盤。

---

#### 5. 確認大戶動向 — 展開「🐳 籌碼面 (13F)」

每張股票卡片的「🐳 籌碼面 (13F)」展開區提供：
- **WhaleWisdom 連結**：一鍵查看完整 13F 機構持倉報告
- **前五大機構持有者**：若資料可取得，直接顯示表格
- 重點觀察：
  - **New / Add（新進 / 加碼）** → 大戶正在佈局
  - **Reduce / Sold Out（減碼 / 清倉）** → 大戶正在撤退

> 💡 跟單要跟「新增」而非庫存。觀察波克夏、橋水、文藝復興等指標性機構。

---

#### 6. 查看財報日與股息

每張股票卡片自動顯示：
- **📅 財報日**：下次財報發布日期，14 天內顯示倒數天數
- **💰 殖利率**（護城河 / 債券類）：當前股息殖利率與除息日

> 💡 財報前後是護城河論點被驗證的關鍵時刻，提前做好準備。

---

#### 7. 記錄觀點 — 展開「📝 觀點版控」

投資決策需要留下紀錄，避免事後偏差：
- 展開股票卡片的「📝 觀點版控」，可查看**完整歷史觀點**（含版本號與日期）
- 每次更新觀點，系統自動遞增版本號（v1 → v2 → v3...）
- 可同時設定**領域標籤**（AI、Cloud、SaaS...），標籤隨觀點一併版控快照

> 💡 定期回顧觀點演進，才能發現自己的盲點與進步。

---

#### 8. 管理清單 — 排序、分類、匯出、匯入

- **↕️ 拖曳排序**：每個分頁頂部勾選「↕️ 拖曳排序」開啟排序模式，拖曳調整後點擊「💾 儲存排序」寫入資料庫
- **🔄 切換分類**：股票卡片內可直接切換分類（例如從風向球移至護城河）
- **🗑️ 移除追蹤**：移除時需填寫原因，移除後可在「📦 已移除」分頁查看歷史
- **🔄 重新啟用**：在「📦 已移除」分頁，可將已移除的股票重新啟用到任意分類
- **📥 匯出觀察名單**：左側面板可下載 JSON 格式的完整觀察名單（含觀點與標籤）
- **📤 匯入觀察名單**：左側面板可上傳 JSON 檔案批次匯入（支援 upsert）

---

#### 9. 每週摘要

每週日 18:00 UTC，系統自動發送 **Telegram 投資組合健康報告**，包含：
- **健康分數**：正常股票佔比（例如 85%）
- **異常股票清單**：目前非 NORMAL 的股票及其訊號
- **本週訊號變化**：過去 7 天內訊號變動的股票與變動次數

> 💡 每週花 5 分鐘看摘要，掌握整體投資組合狀態。
""")


# ---------------------------------------------------------------------------
# Sidebar: 操作面板 (Radar-specific)
# ---------------------------------------------------------------------------

_MARKET_KEYS = list(STOCK_MARKET_OPTIONS.keys())


def _market_label(key: str) -> str:
    return STOCK_MARKET_OPTIONS[key]["label"]


with st.sidebar:
    st.header("🛠️ 操作面板")

    # -- Add Stock / Bond --
    st.subheader("➕ 新增追蹤")

    radar_asset_type = st.radio(
        "資產類型",
        ["📈 股票", "🛡️ 債券"],
        horizontal=True,
        key="radar_asset_type",
    )

    if radar_asset_type == "📈 股票":
        radar_market = st.selectbox(
            "市場",
            options=_MARKET_KEYS,
            format_func=_market_label,
            key="radar_stock_market",
        )
        radar_market_info = STOCK_MARKET_OPTIONS[radar_market]
        st.caption(f"幣別：{radar_market_info['currency']}")

        with st.form("add_stock_form", clear_on_submit=True):
            new_ticker = st.text_input(
                "股票代號",
                placeholder=STOCK_MARKET_PLACEHOLDERS.get(
                    radar_market, "AAPL"
                ),
            )
            new_category = st.selectbox(
                "分類",
                options=STOCK_CATEGORY_OPTIONS,
                format_func=lambda x: CATEGORY_LABELS.get(x, x),
            )
            new_thesis = st.text_area(
                "初始觀點", placeholder="寫下你對這檔股票的看法..."
            )
            new_tags = st.multiselect(
                "🏷️ 初始標籤",
                options=DEFAULT_TAG_OPTIONS,
            )
            submitted = st.form_submit_button("新增")

            if submitted:
                if not new_ticker.strip():
                    st.warning("⚠️ 請輸入股票代號。")
                elif not new_thesis.strip():
                    st.warning("⚠️ 請輸入初始觀點。")
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
                        st.success(f"✅ 已新增 {full_ticker} 到追蹤清單！")
                        refresh_ui()

    else:  # Bond mode
        with st.form("add_bond_form", clear_on_submit=True):
            bond_ticker = st.text_input(
                "債券代號", placeholder="TLT, BND, SGOV"
            )
            bond_currency = st.selectbox(
                "幣別", options=CASH_CURRENCY_OPTIONS
            )
            bond_thesis = st.text_area(
                "初始觀點", placeholder="寫下你對這檔債券的看法..."
            )
            bond_tags = st.multiselect(
                "🏷️ 初始標籤",
                options=DEFAULT_TAG_OPTIONS,
                key="bond_tags",
            )
            bond_submitted = st.form_submit_button("新增")

            if bond_submitted:
                if not bond_ticker.strip():
                    st.warning("⚠️ 請輸入債券代號。")
                elif not bond_thesis.strip():
                    st.warning("⚠️ 請輸入初始觀點。")
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
                            f"✅ 已新增 {bond_ticker.strip().upper()}"
                            " 到追蹤清單！"
                        )
                        refresh_ui()

    st.divider()

    # -- Scan --
    st.subheader("🔍 三層漏斗掃描")
    st.caption(
        "掃描在背景執行，結果將透過 Telegram 推播通知。"
        "系統每 30 分鐘自動掃描一次。"
    )
    if st.button("🚀 執行掃描", use_container_width=True):
        result = api_post("/scan", {})
        if result:
            st.success(f"✅ {result.get('message', '掃描已啟動')}")

    st.divider()

    # -- Export Watchlist --
    st.subheader("📥 匯出觀察名單")
    export_data = api_get_silent("/stocks/export")
    if export_data:
        export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 下載 JSON",
            data=export_json,
            file_name=EXPORT_FILENAME,
            mime="application/json",
            use_container_width=True,
        )
        st.caption(f"共 {len(export_data)} 檔股票（含觀點與標籤）")
    else:
        st.caption("目前無追蹤股票可匯出。")

    st.divider()

    # -- Import Watchlist --
    st.subheader("📤 匯入觀察名單")
    uploaded_file = st.file_uploader(
        "上傳 JSON 檔案",
        type=["json"],
        key="import_file",
        label_visibility="collapsed",
    )
    if uploaded_file is not None:
        try:
            import_data = json.loads(uploaded_file.getvalue().decode("utf-8"))
            if isinstance(import_data, list):
                st.caption(f"偵測到 {len(import_data)} 筆資料。")
                if st.button("📤 確認匯入", use_container_width=True):
                    result = api_post("/stocks/import", import_data)
                    if result:
                        st.success(result.get("message", "✅ 匯入完成"))
                        if result.get("errors"):
                            for err in result["errors"]:
                                st.warning(f"⚠️ {err}")
                        refresh_ui()
            else:
                st.warning("⚠️ JSON 格式錯誤，預期為陣列。")
        except json.JSONDecodeError:
            st.error("❌ 無法解析 JSON 檔案。")

    st.download_button(
        "📋 下載匯入範本",
        data=STOCK_IMPORT_TEMPLATE,
        file_name="stock_import_template.json",
        mime="application/json",
        use_container_width=True,
    )

    st.divider()

    # -- Refresh --
    if st.button("🔄 重新整理畫面", use_container_width=True):
        refresh_ui()


# ---------------------------------------------------------------------------
# Main Dashboard: Stock Tabs
# ---------------------------------------------------------------------------

stocks_data = fetch_stocks()
removed_data = fetch_removed_stocks()

if stocks_data is None:
    st.markdown("---")
    st.warning("⏳ 無法連線至後端服務，可能正在啟動中。")
    st.caption("後端服務通常需要 10–30 秒完成初始化，請點擊下方按鈕重試。")
    if st.button("🔄 重試連線", type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

# Group stocks by category (radar categories only)
category_map = {cat: [] for cat in RADAR_CATEGORY_OPTIONS}
for stock in stocks_data or []:
    cat = stock.get("category", "Growth")
    if cat in category_map:
        category_map[cat].append(stock)

removed_list = removed_data or []

# Build tab labels
tab_labels = [
    f"🌊 風向球 ({len(category_map['Trend_Setter'])})",
    f"🏰 護城河 ({len(category_map['Moat'])})",
    f"🚀 成長夢想 ({len(category_map['Growth'])})",
    f"🛡️ 債券 ({len(category_map['Bond'])})",
    f"📦 已移除 ({len(removed_list)})",
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
                render_stock_card(stock)
        else:
            st.info(
                f"📭 尚無{CATEGORY_LABELS[_cat]}類股票，請在左側面板新增。"
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
                    category_label = CATEGORY_LABELS.get(
                        removed.get("category", ""),
                        removed.get("category", ""),
                    )
                    st.caption(f"分類：{category_label}")
                    removed_at = removed.get("removed_at", "")
                    st.caption(
                        f"移除日期：{removed_at[:10] if removed_at else '未知'}"
                    )

                with col2:
                    st.markdown("**🗑️ 移除原因：**")
                    st.error(removed.get("removal_reason", "未知"))

                    st.markdown("**💡 最後觀點：**")
                    st.info(removed.get("current_thesis", "尚無觀點"))

                    # -- Removal History --
                    with st.expander(
                        f"📜 移除歷史 — {ticker}", expanded=False
                    ):
                        removals = api_get(f"/ticker/{ticker}/removals")
                        if removals:
                            for entry in removals:
                                created = entry.get("created_at", "")
                                st.markdown(
                                    f"**{created[:10] if created else '未知日期'}**"
                                )
                                st.text(entry.get("reason", ""))
                                st.divider()
                        else:
                            st.caption("尚無移除歷史紀錄。")

                    # -- Thesis History --
                    with st.expander(
                        f"📝 觀點歷史 — {ticker}", expanded=False
                    ):
                        history = fetch_thesis_history(ticker)
                        render_thesis_history(history or [])

                    # -- Reactivate --
                    with st.expander(
                        f"🔄 重新啟用 — {ticker}", expanded=False
                    ):
                        reactivate_cat = st.selectbox(
                            "分類",
                            options=CATEGORY_OPTIONS,
                            format_func=lambda x: CATEGORY_LABELS.get(x, x),
                            key=f"reactivate_cat_{ticker}",
                        )
                        reactivate_thesis = st.text_area(
                            "新觀點（選填）",
                            key=f"reactivate_thesis_{ticker}",
                            placeholder="重新啟用時的觀點...",
                        )
                        if st.button(
                            "✅ 確認重新啟用",
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
                                    result.get("message", "✅ 已重新啟用")
                                )
                                refresh_ui()
    else:
        st.info("📭 目前沒有已移除的股票。")
