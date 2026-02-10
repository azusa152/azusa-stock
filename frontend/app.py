"""
Azusa Radar — Streamlit 前端 Dashboard
透過 Backend API 顯示追蹤股票、技術指標與觀點版控。
"""

import json

import pandas as pd
import requests
import streamlit as st
from streamlit_sortables import sort_items

from config import (
    API_DELETE_TIMEOUT,
    API_DIVIDEND_TIMEOUT,
    API_EARNINGS_TIMEOUT,
    API_GET_TIMEOUT,
    API_PATCH_TIMEOUT,
    API_POST_TIMEOUT,
    API_PUT_TIMEOUT,
    API_SIGNALS_TIMEOUT,
    BACKEND_URL,
    BIAS_OVERHEATED_UI,
    BIAS_OVERSOLD_UI,
    CACHE_TTL_ALERTS,
    CACHE_TTL_DIVIDEND,
    CACHE_TTL_EARNINGS,
    CACHE_TTL_MOAT,
    CACHE_TTL_REMOVED,
    CACHE_TTL_SCAN_HISTORY,
    CACHE_TTL_SIGNALS,
    CACHE_TTL_STOCKS,
    CACHE_TTL_THESIS,
    CATEGORY_LABELS,
    CATEGORY_OPTIONS,
    DEFAULT_ALERT_THRESHOLD,
    DEFAULT_TAG_OPTIONS,
    EARNINGS_BADGE_DAYS_THRESHOLD,
    EXPORT_FILENAME,
    MARGIN_BAD_CHANGE_THRESHOLD,
    PRICE_WEAK_BIAS_THRESHOLD,
    SCAN_HISTORY_CARD_LIMIT,
    WHALEWISDOM_STOCK_URL,
)

# ---------------------------------------------------------------------------
# 頁面設定
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="投資雷達 Azusa Radar",
    page_icon="📡",
    layout="wide",
)

st.title("📡 投資雷達 Azusa Radar")
st.caption("V2.0 — 三層漏斗 + 籌碼面訊號")

with st.expander("📖 投資雷達：使用說明書 (SOP)", expanded=False):
    st.markdown("""
### 系統總覽

本系統將股票分為**四大類別**，各自對應不同的追蹤邏輯：

| 分類 | 說明 |
|------|------|
| 🌊 **風向球 (Trend Setter)** | 大盤 ETF、巨頭，觀察資金流向與 Capex |
| 🏰 **護城河 (Moat)** | 供應鏈中不可替代的賣鏟子公司 |
| 🚀 **成長夢想 (Growth)** | 高波動、具想像空間的成長股 |
| 🧺 **ETF** | 指數型基金，被動追蹤市場或特定主題 |

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
- **💰 殖利率**（護城河 / ETF 類）：當前股息殖利率與除息日

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

- **↕️ 拖曳排序**：每個分頁頂部的「↕️ 拖曳排序」可調整股票顯示順位，點擊「💾 儲存排序」寫入資料庫
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
# Helper Functions
# ---------------------------------------------------------------------------

def api_get(path: str) -> dict | list | None:
    """GET 請求 Backend API。"""
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=API_GET_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_post(path: str, json_data: dict) -> dict | None:
    """POST 請求 Backend API。"""
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", json=json_data, timeout=API_POST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_patch(path: str, json_data: dict) -> dict | None:
    """PATCH 請求 Backend API。"""
    try:
        resp = requests.patch(f"{BACKEND_URL}{path}", json=json_data, timeout=API_PATCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_put(path: str, json_data: dict) -> dict | None:
    """PUT 請求 Backend API。"""
    try:
        resp = requests.put(f"{BACKEND_URL}{path}", json=json_data, timeout=API_PUT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


def api_delete(path: str) -> dict | None:
    """DELETE 請求 Backend API。"""
    try:
        resp = requests.delete(f"{BACKEND_URL}{path}", timeout=API_DELETE_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"❌ API 請求失敗：{e}")
        return None


@st.cache_data(ttl=CACHE_TTL_STOCKS, show_spinner="載入股票資料中...")
def fetch_stocks() -> list | None:
    """取得所有追蹤股票（僅 DB 資料）。"""
    return api_get("/stocks")


@st.cache_data(ttl=CACHE_TTL_SIGNALS, show_spinner=False)
def fetch_signals(ticker: str) -> dict | None:
    """取得單一股票的技術訊號（yfinance）。"""
    try:
        resp = requests.get(f"{BACKEND_URL}/ticker/{ticker}/signals", timeout=API_SIGNALS_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_REMOVED, show_spinner="載入已移除股票...")
def fetch_removed_stocks() -> list | None:
    """取得已移除股票清單。"""
    return api_get("/stocks/removed")


@st.cache_data(ttl=CACHE_TTL_EARNINGS, show_spinner=False)
def fetch_earnings(ticker: str) -> dict | None:
    """取得財報日期。"""
    try:
        resp = requests.get(f"{BACKEND_URL}/ticker/{ticker}/earnings", timeout=API_EARNINGS_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_DIVIDEND, show_spinner=False)
def fetch_dividend(ticker: str) -> dict | None:
    """取得股息資訊。"""
    try:
        resp = requests.get(f"{BACKEND_URL}/ticker/{ticker}/dividend", timeout=API_DIVIDEND_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=CACHE_TTL_MOAT, show_spinner=False)
def fetch_moat(ticker: str) -> dict | None:
    """取得護城河分析資料。"""
    return api_get(f"/ticker/{ticker}/moat")


@st.cache_data(ttl=CACHE_TTL_SCAN_HISTORY, show_spinner=False)
def fetch_scan_history(ticker: str, limit: int = SCAN_HISTORY_CARD_LIMIT) -> list | None:
    """取得掃描歷史。"""
    return api_get(f"/ticker/{ticker}/scan-history?limit={limit}")


@st.cache_data(ttl=CACHE_TTL_ALERTS, show_spinner=False)
def fetch_alerts(ticker: str) -> list | None:
    """取得價格警報列表。"""
    return api_get(f"/ticker/{ticker}/alerts")


@st.cache_data(ttl=CACHE_TTL_THESIS, show_spinner=False)
def fetch_thesis_history(ticker: str) -> list | None:
    """取得觀點版控歷史。"""
    return api_get(f"/ticker/{ticker}/thesis")


# ---------------------------------------------------------------------------
# Sidebar: 新增股票 & 掃描
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🛠️ 操作面板")

    # -- 新增股票 --
    st.subheader("➕ 新增追蹤股票")
    with st.form("add_stock_form", clear_on_submit=True):
        new_ticker = st.text_input("股票代號", placeholder="例如 AAPL, TSM, NVDA")
        new_category = st.selectbox(
            "分類",
            options=CATEGORY_OPTIONS,
            format_func=lambda x: CATEGORY_LABELS.get(x, x),
        )
        new_thesis = st.text_area("初始觀點", placeholder="寫下你對這檔股票的看法...")
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
                result = api_post("/ticker", {
                    "ticker": new_ticker.strip().upper(),
                    "category": new_category,
                    "thesis": new_thesis.strip(),
                    "tags": new_tags,
                })
                if result:
                    st.success(f"✅ 已新增 {new_ticker.upper()} 到追蹤清單！")
                    st.rerun()

    st.divider()

    # -- 全域掃描 (V2 三層漏斗) --
    st.subheader("🔍 三層漏斗掃描")
    st.caption("掃描在背景執行，結果將透過 Telegram 推播通知。系統每 30 分鐘自動掃描一次。")
    if st.button("🚀 執行掃描", use_container_width=True):
        result = api_post("/scan", {})
        if result:
            st.success(f"✅ {result.get('message', '掃描已啟動')}")

    st.divider()

    # -- 匯出觀察名單 --
    st.subheader("📥 匯出觀察名單")
    export_data = api_get("/stocks/export")
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

    # -- 匯入觀察名單 --
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
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/stocks/import",
                            json=import_data,
                            timeout=API_POST_TIMEOUT,
                        )
                        resp.raise_for_status()
                        result = resp.json()
                    except requests.RequestException as e:
                        st.error(f"❌ 匯入失敗：{e}")
                        result = None
                    if result:
                        st.success(result.get("message", "✅ 匯入完成"))
                        if result.get("errors"):
                            for err in result["errors"]:
                                st.warning(f"⚠️ {err}")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("⚠️ JSON 格式錯誤，預期為陣列。")
        except json.JSONDecodeError:
            st.error("❌ 無法解析 JSON 檔案。")

    st.divider()

    # -- 重新整理資料 --
    st.subheader("🔄 資料快取")
    st.caption("股票資料快取 5 分鐘，過期後下次操作時自動重新載入。點擊下方按鈕可立即刷新。")
    if st.button("🔄 立即刷新資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Main Dashboard: 股票清單 (Tabs)
# ---------------------------------------------------------------------------

stocks_data = fetch_stocks()
removed_data = fetch_removed_stocks()

if stocks_data is None:
    st.info("⏳ 無法連線至後端服務，請確認 Backend 是否啟動。")
    st.stop()

# 依分類分組
category_map = {
    "Trend_Setter": [],
    "Moat": [],
    "Growth": [],
    "ETF": [],
}
for stock in (stocks_data or []):
    cat = stock.get("category", "Growth")
    if cat in category_map:
        category_map[cat].append(stock)

removed_list = removed_data or []

tab_trend, tab_moat, tab_growth, tab_etf, tab_archive = st.tabs([
    f"🌊 風向球 ({len(category_map['Trend_Setter'])})",
    f"🏰 護城河 ({len(category_map['Moat'])})",
    f"🚀 成長夢想 ({len(category_map['Growth'])})",
    f"🧺 ETF ({len(category_map['ETF'])})",
    f"📦 已移除 ({len(removed_list)})",
])


def render_thesis_history(history: list[dict]) -> None:
    """渲染觀點版控歷史紀錄（共用於主卡片與已移除卡片）。"""
    if history:
        st.markdown("**📜 歷史觀點紀錄：**")
        for entry in history:
            ver = entry.get("version", "?")
            content = entry.get("content", "")
            created = entry.get("created_at", "")
            entry_tags = entry.get("tags", [])
            st.markdown(
                f"**v{ver}** ({created[:10] if created else '未知日期'})"
            )
            if entry_tags:
                st.caption(
                    "標籤：" + " ".join(f"`{t}`" for t in entry_tags)
                )
            st.text(content)
            st.divider()
    else:
        st.caption("尚無歷史觀點紀錄。")


def render_stock_card(stock: dict) -> None:
    """渲染單一股票卡片，包含技術指標與觀點編輯。"""
    ticker = stock["ticker"]
    signals = fetch_signals(ticker) or {}

    with st.container(border=True):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.subheader(f"📊 {ticker}")
            st.caption(f"分類：{stock['category']}")

            # 動態標籤
            current_tags = stock.get("current_tags", [])
            if current_tags:
                tag_badges = " ".join(
                    f"`{tag}`" for tag in current_tags
                )
                st.markdown(f"🏷️ {tag_badges}")

            if "error" in signals:
                st.warning(signals["error"])
            else:
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

                # 籌碼面指標
                chip_col1, chip_col2 = st.columns(2)
                with chip_col1:
                    if bias is not None:
                        bias_color = "🔴" if bias > BIAS_OVERHEATED_UI else ("🟢" if bias < BIAS_OVERSOLD_UI else "⚪")
                        st.metric(f"{bias_color} 乖離率 Bias", f"{bias}%")
                    else:
                        st.metric("乖離率 Bias", "N/A")
                with chip_col2:
                    if volume_ratio is not None:
                        st.metric("量比 Vol Ratio", f"{volume_ratio}x")
                    else:
                        st.metric("量比 Vol Ratio", "N/A")

                # 狀態列表
                for s in signals.get("status", []):
                    st.write(s)

            # -- 財報日曆 & 股息 --
            info_cols = st.columns(2)
            earnings_data = fetch_earnings(ticker)
            earnings_date_str = (
                earnings_data.get("earnings_date") if earnings_data else None
            )
            with info_cols[0]:
                if earnings_date_str:
                    from datetime import datetime as dt
                    try:
                        ed = dt.strptime(earnings_date_str, "%Y-%m-%d")
                        days_left = (ed - dt.now()).days
                        badge = f" ({days_left}天)" if 0 < days_left <= EARNINGS_BADGE_DAYS_THRESHOLD else ""
                        st.caption(f"📅 財報日：{earnings_date_str}{badge}")
                    except ValueError:
                        st.caption(f"📅 財報日：{earnings_date_str}")
                else:
                    st.caption("📅 財報日：N/A")

            cat = stock.get("category", "")
            with info_cols[1]:
                if cat in ("Moat", "ETF"):
                    div_data = fetch_dividend(ticker)
                    if div_data and div_data.get("dividend_yield"):
                        dy = div_data["dividend_yield"]
                        ex_date = div_data.get("ex_dividend_date", "N/A")
                        st.caption(f"💰 殖利率：{dy}% | 除息日：{ex_date}")
                    else:
                        st.caption("💰 殖利率：N/A")

            # -- 籌碼面 (13F) --
            with st.expander(f"🐳 籌碼面 (13F) — {ticker}", expanded=False):
                st.link_button(
                    f"🐳 前往 WhaleWisdom 查看大戶動向",
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
                        "⚠️ 機構持倉資料暫時無法取得，請點擊上方按鈕前往 WhaleWisdom 查看完整 13F 報告。"
                    )

            # -- 護城河檢測 (Moat Health Check) -- ETF 不適用
            if stock.get("category") != "ETF":
                with st.expander(f"🏰 護城河檢測 — {ticker}", expanded=False):
                    moat_data = fetch_moat(ticker)

                    if moat_data and moat_data.get("moat") != "N/A":
                        # 1) 毛利率指標 + YoY 變化
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

                        # 2) 5 季走勢折線圖
                        trend = moat_data.get("margin_trend", [])
                        valid_trend = [t for t in trend if t.get("value") is not None]
                        if valid_trend:
                            df = pd.DataFrame(valid_trend).set_index("date")
                            df.columns = ["毛利率 (%)"]
                            st.line_chart(df)
                        else:
                            st.caption("⚠️ 毛利率趨勢資料不足，無法繪圖。")

                        # 3) 投資診斷 (Azusa Diagnosis)
                        bias_val = signals.get("bias")
                        price_is_weak = bias_val is not None and bias_val < PRICE_WEAK_BIAS_THRESHOLD
                        margin_is_strong = (
                            margin_change is not None and margin_change > 0
                        )
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
                            st.success(
                                "🟢 **護城河穩固**："
                                "毛利率 YoY 成長，基本面健康。"
                            )
                        elif price_is_weak:
                            st.warning(
                                "🟡 **股價偏弱**："
                                "乖離率偏低但護城河數據持平，留意後續季報。"
                            )
                        else:
                            st.info("⚪ **觀察中**：護城河數據持平，持續觀察。")

                        # 補充詳情
                        details = moat_data.get("details", "")
                        if details:
                            st.caption(f"📊 {details}")
                    else:
                        st.warning(
                            "⚠️ 無法取得財報數據（可能是新股），請稍後再試。"
                        )

            # -- 掃描歷史 --
            with st.expander(f"📈 掃描歷史 — {ticker}", expanded=False):
                scan_hist = fetch_scan_history(ticker)
                if scan_hist:
                    # 計算連續次數
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
                        sig_icon = {
                            "THESIS_BROKEN": "🔴",
                            "CONTRARIAN_BUY": "🟢",
                            "OVERHEATED": "🟠",
                            "NORMAL": "⚪",
                        }.get(sig, "⚪")
                        date_str = scanned[:16] if scanned else "N/A"
                        st.caption(f"{sig_icon} {sig} — {date_str}")
                else:
                    st.caption("尚無掃描紀錄。")

            # -- 自訂價格警報 --
            with st.expander(f"🔔 價格警報 — {ticker}", expanded=False):
                alerts = fetch_alerts(ticker)
                if alerts:
                    st.markdown("**目前警報：**")
                    for a in alerts:
                        op_str = "<" if a["operator"] == "lt" else ">"
                        active_badge = "🟢" if a["is_active"] else "⚪"
                        triggered = a.get("last_triggered_at")
                        trigger_info = (
                            f"（上次觸發：{triggered[:10]}）" if triggered else ""
                        )
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.caption(
                                f"{active_badge} {a['metric']} {op_str} "
                                f"{a['threshold']}{trigger_info}"
                            )
                        with col_b:
                            if st.button(
                                "🗑️",
                                key=f"del_alert_{a['id']}",
                                help="刪除此警報",
                            ):
                                api_delete(f"/alerts/{a['id']}")
                                st.rerun()
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
                        {
                            "metric": alert_metric,
                            "operator": alert_op,
                            "threshold": alert_threshold,
                        },
                    )
                    if result:
                        st.success(result.get("message", "✅ 警報已建立"))
                        st.rerun()

        with col2:
            st.markdown("**💡 當前觀點：**")
            st.info(stock.get("current_thesis", "尚無觀點"))

            # -- 觀點歷史與編輯 --
            with st.expander(f"📝 觀點版控 — {ticker}", expanded=False):
                # 取得歷史紀錄
                history = fetch_thesis_history(ticker)

                render_thesis_history(history or [])

                # 新增觀點
                st.markdown("**✏️ 新增觀點：**")
                new_thesis_content = st.text_area(
                    "觀點內容",
                    key=f"thesis_input_{ticker}",
                    placeholder="寫下你對這檔股票的最新看法...",
                    label_visibility="collapsed",
                )

                # 標籤編輯
                all_tag_options = sorted(
                    set(DEFAULT_TAG_OPTIONS + current_tags)
                )
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
                            {
                                "content": new_thesis_content.strip(),
                                "tags": selected_tags,
                            },
                        )
                        if result:
                            st.success(result.get("message", "✅ 觀點已更新"))
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.warning("⚠️ 請輸入觀點內容。")

            # -- 切換分類 --
            with st.expander(f"🔄 切換分類 — {ticker}", expanded=False):
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
                        f"/ticker/{ticker}/category",
                        {"category": new_cat},
                    )
                    if result:
                        st.success(result.get("message", "✅ 分類已切換"))
                        st.cache_data.clear()
                        st.rerun()

            # -- 移除追蹤 --
            with st.expander(f"🗑️ 移除追蹤 — {ticker}", expanded=False):
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
                            st.rerun()
                    else:
                        st.warning("⚠️ 請輸入移除原因。")


def render_reorder_section(category_key: str, stocks_in_cat: list[dict]) -> None:
    """渲染拖曳排序區塊。"""
    if len(stocks_in_cat) < 2:
        return
    with st.expander("↕️ 拖曳排序", expanded=False):
        ticker_list = [s["ticker"] for s in stocks_in_cat]
        sorted_tickers = sort_items(ticker_list, key=f"sort_{category_key}")
        if sorted_tickers != ticker_list:
            if st.button("💾 儲存排序", key=f"save_order_{category_key}"):
                result = api_put("/stocks/reorder", {"ordered_tickers": sorted_tickers})
                if result:
                    st.success(result.get("message", "✅ 排序已儲存"))
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.caption("拖曳股票代號以調整顯示順序。")


# -- 渲染各 Tab（迴圈化） --
_category_tabs = [tab_trend, tab_moat, tab_growth, tab_etf]
for _cat, _tab in zip(CATEGORY_OPTIONS, _category_tabs):
    with _tab:
        _stocks = category_map[_cat]
        if _stocks:
            render_reorder_section(_cat, _stocks)
            for stock in _stocks:
                render_stock_card(stock)
        else:
            st.info(f"📭 尚無{CATEGORY_LABELS[_cat]}類股票，請在左側面板新增。")

with tab_archive:
    if removed_list:
        for removed in removed_list:
            ticker = removed["ticker"]
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.subheader(f"📦 {ticker}")
                    category_label = CATEGORY_LABELS.get(
                        removed.get("category", ""), removed.get("category", "")
                    )
                    st.caption(f"分類：{category_label}")
                    removed_at = removed.get("removed_at", "")
                    st.caption(f"移除日期：{removed_at[:10] if removed_at else '未知'}")

                with col2:
                    st.markdown("**🗑️ 移除原因：**")
                    st.error(removed.get("removal_reason", "未知"))

                    st.markdown("**💡 最後觀點：**")
                    st.info(removed.get("current_thesis", "尚無觀點"))

                    # -- 移除歷史 --
                    with st.expander(f"📜 移除歷史 — {ticker}", expanded=False):
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

                    # -- 觀點歷史 --
                    with st.expander(f"📝 觀點歷史 — {ticker}", expanded=False):
                        history = fetch_thesis_history(ticker)
                        render_thesis_history(history or [])

                    # -- 重新啟用 --
                    with st.expander(f"🔄 重新啟用 — {ticker}", expanded=False):
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
                                st.success(result.get("message", "✅ 已重新啟用"))
                                st.cache_data.clear()
                                st.rerun()
    else:
        st.info("📭 目前沒有已移除的股票。")
