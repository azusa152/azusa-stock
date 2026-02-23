---
name: folio
description: Folio 智能資產配置 — 股票追蹤、掃描、警報與外匯監控系統
version: 1.1.0
---

# Folio Skill

Folio 是一套自架的投資追蹤系統，提供股票觀察名單管理、三層漏斗掃描、護城河分析、價格警報、外匯換匯時機監控、以及 Telegram 通知。

## Prerequisites

- Folio 的 Docker Compose 服務正在運行
- Backend API 預設在 `http://localhost:8000`
- (Optional) Set `FOLIO_API_KEY` environment variable for production security

## Authentication

Folio supports optional API key authentication via the `X-API-Key` header.

**Dev Mode (default):** If `FOLIO_API_KEY` is unset, authentication is disabled.

**Production Mode:** Set `FOLIO_API_KEY` in `.env` and include it in all requests:

```bash
# Generate API key
make generate-key

# Add to .env
echo "FOLIO_API_KEY=your-key-here" >> .env

# Export for shell commands
export FOLIO_API_KEY="your-key-here"
```

All `curl` commands below assume you'll add `-H "X-API-Key: $FOLIO_API_KEY"` when auth is enabled.

## Language (i18n)

Folio supports 4 languages. All API response messages and Telegram notifications are localized based on the user's saved preference.

| Code | Language |
|------|----------|
| `zh-TW` | 繁體中文 (default) |
| `en` | English |
| `ja` | 日本語 |
| `zh-CN` | 简体中文 |

**Read current language:**

```bash
curl -s http://localhost:8000/settings/preferences \
  -H "X-API-Key: $FOLIO_API_KEY"
# Response includes: {"language": "zh-TW", ...}
```

**Change language:**

```bash
curl -s -X PUT http://localhost:8000/settings/preferences \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"language": "en"}'
```

> **Note:** The `detail` field in error responses is localized — its language varies per user. Always branch on `error_code`, not `detail`.

## Quick Start

### 查看投資組合摘要

```bash
curl -s http://localhost:8000/summary \
  -H "X-API-Key: $FOLIO_API_KEY"
```

### 透過 Webhook 執行操作

```bash
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action": "summary"}'
```

## Webhook Actions

`POST /webhook` 是統一入口，接受 JSON body：

```json
{
  "action": "string",
  "ticker": "string (optional)",
  "params": {}
}
```

### Supported Actions

| Action | Description | Requires `ticker` | Example |
|--------|-------------|-------------------|---------|
| `help` | 列出所有支援的 actions 與參數 | No | `{"action": "help"}` |
| `summary` | 投資組合健康摘要 | No | `{"action": "summary"}` |
| `signals` | 單一股票技術指標 | Yes | `{"action": "signals", "ticker": "NVDA"}` |
| `scan` | 觸發全域掃描（背景執行） | No | `{"action": "scan"}` |
| `moat` | 護城河分析（毛利率 YoY） | Yes | `{"action": "moat", "ticker": "TSM"}` |
| `alerts` | 查看價格警報 | Yes | `{"action": "alerts", "ticker": "AAPL"}` |
| `fear_greed` | 恐懼與貪婪指數 (VIX + CNN 綜合) | No | `{"action": "fear_greed"}` |
| `add_stock` | 新增股票到觀察名單 | Yes (in params) | See below |
| `withdraw` | 聰明提款建議 (Liquidity Waterfall) | No | See below |
| `fx_watch` | 外匯監控：檢查所有監控配置並發送 Telegram 警報 | No | `{"action": "fx_watch"}` |

> **Tip:** Use `help` first to discover all supported actions and their parameters at runtime.

### add_stock Example

```json
{
  "action": "add_stock",
  "params": {
    "ticker": "AMD",
    "category": "Moat",
    "thesis": "ASIC 與 AI GPU 的強力競爭者",
    "tags": ["AI", "Semiconductor"]
  }
}
```

### withdraw Example

```json
{
  "action": "withdraw",
  "params": {
    "amount": 50000,
    "currency": "TWD"
  }
}
```

Returns a prioritized sell plan: (1) overweight rebalancing, (2) tax-loss harvesting, (3) liquidity order. Each recommendation includes ticker, quantity, sell value, reason, and unrealized P/L.

### fx_watch Example

```json
{
  "action": "fx_watch"
}
```

Analyzes all active FX watch configurations and sends Telegram alerts for currency pairs meeting alert conditions (near recent high or consecutive increases). Response includes `total_watches`, `triggered_alerts`, and `sent_alerts` counts. Subject to cooldown mechanism — same config won't re-alert within its `reminder_interval_hours`.

### Response Format

All webhook responses follow this structure:

```json
{
  "success": true,
  "message": "Human-readable result",
  "data": {}
}
```

### Error Response Format

Direct API endpoints return structured errors with a machine-readable `error_code`:

```json
{
  "detail": {
    "error_code": "STOCK_NOT_FOUND",
    "detail": "找不到股票 NVDA。"
  }
}
```

Use `error_code` for programmatic branching instead of parsing the human-readable `detail` string.

Common error codes: `STOCK_NOT_FOUND`, `STOCK_ALREADY_EXISTS`, `STOCK_ALREADY_INACTIVE`, `STOCK_ALREADY_ACTIVE`, `CATEGORY_UNCHANGED`, `HOLDING_NOT_FOUND`, `PROFILE_NOT_FOUND`, `SCAN_IN_PROGRESS`, `TELEGRAM_NOT_CONFIGURED`, `PREFERENCES_UPDATE_FAILED`.

## Direct API Endpoints

For advanced use, you can call individual endpoints directly:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/summary` | 純文字投資組合摘要（含總值+日漲跌+前三名+配置偏移+Smart Money） |
| `GET` | `/stocks` | 所有追蹤中股票清單（含 `last_scan_signal` 持久化訊號） |
| `GET` | `/stocks/export` | 匯出觀察名單 (JSON) |
| `POST` | `/ticker` | 新增股票 |
| `GET` | `/ticker/{ticker}/signals` | 技術訊號 (RSI, MA, Bias) |
| `GET` | `/ticker/{ticker}/moat` | 護城河分析 |
| `POST` | `/ticker/{ticker}/thesis` | 更新觀點 |
| `PATCH` | `/ticker/{ticker}/category` | 切換分類 |
| `POST` | `/scan` | 觸發全域掃描 |
| `GET` | `/market/fear-greed` | 恐懼與貪婪指數（VIX + CNN 綜合分析） |
| `GET` | `/scan/last` | 取得最近一次掃描時間戳與市場情緒（判斷資料新鮮度，含 F&G） |
| `POST` | `/digest` | 觸發每週摘要 |
| `GET` | `/snapshots` | 歷史投資組合快照（`?days=30` 或 `?start=&end=`，最多 730 天） |
| `GET` | `/snapshots/twr` | 時間加權報酬率（`?start=&end=`，預設 YTD；`twr_pct` 為 null 時表示快照不足） |
| `POST` | `/snapshots/take` | 手動觸發當日快照（背景執行，每日 upsert） |
| `GET` | `/ticker/{ticker}/scan-history` | 掃描歷史 |
| `GET` | `/ticker/{ticker}/alerts` | 價格警報清單 |
| `POST` | `/ticker/{ticker}/alerts` | 建立價格警報 |
| `PATCH` | `/alerts/{alert_id}/toggle` | 切換警報啟用狀態（active ↔ paused） |
| `DELETE` | `/alerts/{alert_id}` | 刪除價格警報 |
| `GET` | `/ticker/{ticker}/earnings` | 財報日曆 |
| `GET` | `/ticker/{ticker}/dividend` | 股息資訊 |
| `GET` | `/personas/templates` | 投資人格範本列表 |
| `GET` | `/profiles` | 目前啟用的投資組合配置 |
| `POST` | `/profiles` | 建立投資組合配置 |
| `GET` | `/holdings` | 所有持倉 |
| `POST` | `/holdings` | 新增持倉（含可選 broker / currency 欄位，currency 預設 USD） |
| `POST` | `/holdings/cash` | 新增現金持倉 |
| `GET` | `/rebalance` | 再平衡分析 + X-Ray 穿透式持倉，支援 `?display_currency=TWD`。回傳含 `xray` 陣列、`total_value_change_pct`（日漲跌）、`holdings_detail[].cost_total`（總成本） |
| `POST` | `/rebalance/xray-alert` | 觸發 X-Ray 分析並發送 Telegram 集中度風險警告 |
| `GET` | `/stress-test` | 壓力測試分析：模擬大盤崩盤情境，支援 `?scenario_drop_pct=-20&display_currency=USD`。回傳組合 Beta、預期損失金額與百分比、痛苦等級（微風輕拂/有感修正/傷筋動骨/睡不著覺）、各持倉明細與建議 |
| `GET` | `/currency-exposure` | 匯率曝險分析：含 `breakdown`（全資產）+ `cash_breakdown`（現金）幣別分佈、`fx_rate_alerts`（三層級警報）、匯率變動、建議 |
| `POST` | `/currency-exposure/alert` | 檢查匯率曝險並發送 Telegram 警報（三層級偵測：單日 >1.5% / 5日 >2% / 3月 >8%，含現金曝險金額） |
| `POST` | `/withdraw` | 聰明提款建議（Liquidity Waterfall），body: `{"target_amount": 50000, "display_currency": "TWD", "notify": true}` |
| `GET` | `/fx-watch` | 所有外匯監控配置，支援 `?active_only=true` 篩選啟用中 |
| `POST` | `/fx-watch` | 新增外匯監控配置，body: `{"base_currency": "USD", "quote_currency": "TWD", "recent_high_days": 30, "consecutive_increase_days": 3, "alert_on_recent_high": true, "alert_on_consecutive_increase": true, "reminder_interval_hours": 24}` |
| `PATCH` | `/fx-watch/{watch_id}` | 更新外匯監控配置（部分更新），可更新 `recent_high_days`、`consecutive_increase_days`、`alert_on_recent_high`、`alert_on_consecutive_increase`、`reminder_interval_hours`、`is_active` |
| `DELETE` | `/fx-watch/{watch_id}` | 刪除外匯監控配置 |
| `POST` | `/fx-watch/check` | 分析所有啟用中的外匯監控（不發送通知），回傳每筆配置的換匯建議、當前匯率、是否達高點、連續上漲天數 |
| `POST` | `/fx-watch/alert` | 分析外匯監控並發送 Telegram 警報（受冷卻機制限制），回傳 `total_watches`、`triggered_alerts`、`sent_alerts` |
| `GET` | `/settings/telegram` | Telegram 通知設定（token 遮蔽） |
| `PUT` | `/settings/telegram` | 更新 Telegram 通知設定（雙模式） |
| `POST` | `/settings/telegram/test` | 發送 Telegram 測試訊息 |
| `GET` | `/settings/preferences` | 使用者偏好設定（語言、隱私模式等） |
| `PUT` | `/settings/preferences` | 更新使用者偏好設定（upsert），支援 `language` 欄位 (`zh-TW`/`en`/`ja`/`zh-CN`) |
| `GET` | `/docs` | Swagger UI (互動式 API 文件) |
| `GET` | `/openapi.json` | OpenAPI 規範 |
| `GET` | `/gurus` | 取得所有追蹤大師清單（id, name, display_name, cik, active） |
| `POST` | `/gurus` | 新增自訂大師，body: `{"name": "Berkshire Hathaway Inc", "cik": "0001067983", "display_name": "Warren Buffett"}` |
| `DELETE` | `/gurus/{guru_id}` | 停用大師追蹤（不刪除歷史持倉資料） |
| `POST` | `/gurus/sync` | 觸發所有大師 13F 批次同步（SEC EDGAR，帶 mutex 防重複；申報季自動呼叫） |
| `POST` | `/gurus/{guru_id}/sync` | 觸發單一大師 13F 同步，回傳 `{"status": "synced"\|"skipped", "message": "..."}` |
| `GET` | `/gurus/{guru_id}/filing` | 最新 13F 申報摘要：report_date, filing_date, total_value, holdings_count, new_positions, sold_out, increased, decreased |
| `GET` | `/gurus/{guru_id}/holdings` | 所有持倉（含 action: NEW_POSITION/SOLD_OUT/INCREASED/DECREASED/UNCHANGED，ticker, value, shares, change_pct, weight_pct） |
| `GET` | `/gurus/{guru_id}/top` | 前 N 大持倉（按 weight_pct 排序），支援 `?n=10` |
| `GET` | `/resonance` | 投資組合共鳴總覽 — 所有大師 vs 觀察清單/持倉的重疊，回傳 `{results: [{guru_display_name, overlapping_tickers, overlap_count, holdings: [{ticker, action, weight_pct, ...}]}], total_gurus, gurus_with_overlap}` |
| `GET` | `/resonance/{ticker}` | 特定股票的大師持有情況 — 哪些大師持有此股票及其動作 |

## Categories

| Category | Label | Description |
|----------|-------|-------------|
| `Trend_Setter` | 🌊 風向球 | 大盤 ETF、巨頭 |
| `Moat` | 🏰 護城河 | 不可替代的賣鏟子公司 |
| `Growth` | 🚀 成長夢想 | 高波動成長股 |
| `Bond` | 🛡️ 債券 | 國債、投資等級債券 ETF |
| `Cash` | 💵 現金 | 閒置現金 |

## Daily Change Tracking (New)

The following endpoints now include daily change fields calculated from yfinance historical data (previous trading day close vs. current close):

### GET `/ticker/{ticker}/signals` — Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `price` | float | Current close price |
| `previous_close` | float? | Previous trading day close price |
| `change_pct` | float? | Daily change percentage (e.g., `2.50` = +2.50% gain) |
| `rsi` | float | RSI(14) indicator |
| `ma200` | float | 200-day moving average |
| `ma60` | float | 60-day moving average |
| `bias` | float | Price deviation from 60MA (%) |
| `volume_ratio` | float | Recent/average volume ratio |
| `status` | list[str] | Formatted status descriptions |
| `bias_percentile` | float? | Current bias rank in 3-year historical distribution (0–100). e.g., `97.0` = top 3% historically |
| `is_rogue_wave` | bool | `true` when `bias_percentile ≥ 95` AND `volume_ratio ≥ 1.5` — extreme overheating with volume surge |

### GET `/rebalance` — Response Fields (New)

| Field | Type | Description |
|-------|------|-------------|
| `total_value` | float | Current portfolio total market value |
| `previous_total_value` | float? | Previous trading day portfolio total value |
| `total_value_change` | float? | Portfolio total value daily change amount |
| `total_value_change_pct` | float? | Portfolio daily change percentage |
| `holdings_detail[].change_pct` | float? | Per-holding daily change percentage |

**Edge Cases:**
- `previous_close` and `change_pct` will be `null` for newly added stocks with insufficient history (< 2 days)
- Weekend/holiday gaps are automatically handled by yfinance (uses last trading day)
- Cash holdings have no price change (same current and previous value)

## Usage Tips

- Use `fear_greed` to check market sentiment via VIX + CNN Fear & Greed Index before making buy/sell decisions ("be greedy when others are fearful")
- Use `summary` first to get a rich plain-text overview: portfolio value + daily change, category groups, active signals, top movers, allocation drift warnings, and Smart Money highlights
- Use `signals` to check a stock's technical indicators; interpret the scan signal using the **Signal Taxonomy** section below
- Use `moat` to verify if a stock's fundamentals (gross margin) are still intact
- Use `scan` to trigger a full portfolio analysis with Telegram notifications
- Use `rebalance` to check if portfolio allocation drifts from target. The response includes an `xray` array showing true exposure per stock (direct + indirect via ETFs)
- Add `?display_currency=TWD` to `/rebalance` to see all values in TWD (supports USD, TWD, JPY, EUR, GBP, CNY, HKD, SGD, THB)
- Use `POST /rebalance/xray-alert` to trigger Telegram warnings for stocks whose true exposure (direct + ETF indirect) exceeds 15%
- When adding holdings, set `currency` field to match the holding's native currency (e.g., "TWD" for Taiwan stocks, "JPY" for Japan stocks)
- Use `GET /currency-exposure` to check currency concentration risk; response includes `cash_breakdown` (cash-only), `breakdown` (full portfolio), and `fx_rate_alerts` (three-tier rate-change alerts) for separate analysis
- Use `POST /currency-exposure/alert` to trigger Telegram alerts for three-tier FX rate changes (daily spike >1.5%, 5-day swing >2%, 3-month trend >8%), alerts include cash exposure amounts
- Use `POST /fx-watch` to set up FX timing monitors — supports 9 currencies (USD, TWD, JPY, EUR, GBP, CNY, HKD, SGD, THB) in any pair combination
- Use `POST /fx-watch/check` to analyze all active monitors without sending notifications — good for quick market checks
- Use `POST /fx-watch/alert` to trigger Telegram alerts for FX timing opportunities (near recent high or consecutive increases); subject to cooldown (`reminder_interval_hours`)
- Use `PATCH /fx-watch/{id}` with `{"is_active": false}` to temporarily pause a monitor without deleting it
- Use `withdraw` when you need cash — tell it the amount and currency (e.g., `{"amount": 50000, "currency": "TWD"}`), it will recommend which holdings to sell using a 3-tier priority: overweight rebalancing, tax-loss harvesting, then liquidity order
- When `is_rogue_wave` is `true` in a `signals` response, warn the user: bias is at a historically extreme level (≥ 95th percentile) with volume surge — the party is likely peaking; avoid leveraged chasing and consider reducing exposure
- Use `GET /stress-test?scenario_drop_pct=-20&display_currency=USD` to simulate portfolio stress under market crash scenarios (-50% to 0%). Response includes portfolio Beta, expected loss amount/percentage, pain level classification, per-holding breakdown with Beta values, and advice for high-risk portfolios. Supports multi-currency display (USD, TWD, JPY, EUR, GBP, CNY, HKD, SGD, THB)
- Use `PATCH /alerts/{alert_id}/toggle` to pause or resume an individual price alert without deleting it — useful for silencing an alert during earnings season or a known volatile period
- Use `make backup` before any destructive operation (e.g., `docker compose down -v`)
- When users report errors after an upgrade, check `docker compose logs backend --tail 50` first
- Use `GET /resonance` to check which gurus hold the same stocks as the user — response is guru-centric; invert on client side to get per-ticker guru list
- Use `POST /gurus/{guru_id}/sync` to fetch the latest 13F data from SEC EDGAR for a specific guru — status `"synced"` means new data was fetched, `"skipped"` means already up to date
- During 13F filing seasons (February, May, August, November), the cron service automatically calls `POST /gurus/sync` daily; off-season it runs weekly

## Signal Taxonomy

Folio uses two signal fields per stock:

- **`last_scan_signal`** — persisted result of the last full scan (moat + RSI + bias). Returned by `GET /stocks` and `GET /summary`. Used in weekly digest and Telegram notifications.
- **`computed_signal`** — real-time signal recomputed on each request from live RSI/bias (moat excluded for performance). Returned by `GET /stocks/enriched`. The dashboard Signal Alerts section and radar page prefer `computed_signal` when available, falling back to `last_scan_signal`. `THESIS_BROKEN` is always taken from the persisted value (requires moat analysis to set).

Both fields share the same 9-state cascade. Higher priority (lower P number) trumps lower priority when multiple conditions apply.

**Category-aware RSI offsets** are applied to all RSI thresholds (buy and sell side): Growth +2, Moat +1, Trend_Setter 0, Bond −3, Cash 0. For example, Growth stocks need RSI < 37 (not 35) for CONTRARIAN_BUY, and RSI > 72 (not 70) for OVERHEATED.

**MA200 amplifier (Phase 2)**: After the priority cascade, if `bias_200` (price deviation from 200-day MA) is available, it can upgrade signals: buy-side when bias_200 < −15% (WEAKENING→APPROACHING_BUY, APPROACHING_BUY→CONTRARIAN_BUY); sell-side when bias_200 > +20% (CAUTION_HIGH→OVERHEATED, asymmetric threshold due to positive market drift).

| Priority | Signal | Icon | Condition (default offset=0) | Meaning |
|----------|--------|------|------------------------------|---------|
| P1 | `THESIS_BROKEN` | 🚨 | Gross margin YoY deteriorated >2pp | Fundamental thesis is broken — re-evaluate holding |
| P2 | `DEEP_VALUE` | 💎 | Bias < −20% AND RSI < 35 | Both indicators confirm deep discount — highest-conviction entry opportunity |
| P3 | `OVERSOLD` | 📉 | Bias < −20% (RSI ≥ 35) | Price at extreme discount (bias-only); watch for RSI confirmation before acting |
| P4 | `CONTRARIAN_BUY` | 🟢 | RSI < 35 AND Bias < 20% | RSI oversold but price not overheated — potential contrarian entry |
| P4.5 | `APPROACHING_BUY` | 🎯 | RSI < 37 AND Bias < −15% | Accumulation zone — entering buy range; monitor for RSI confirmation |
| P5 | `OVERHEATED` | 🔥 | Bias > 20% AND RSI > 70 | Both indicators confirm overheating — highest-conviction sell warning |
| P6 | `CAUTION_HIGH` | ⚠️ | Bias > 20% OR RSI > 70 | Single indicator elevated — reduce new positions, tighten stops |
| P7 | `WEAKENING` | 🔻 | Bias < −15% AND RSI < 38 | Early weakness — monitor closely, not yet at extreme levels |
| P8 | `NORMAL` | ➖ | Everything else | No notable technical signal |

### Volume Confidence Qualifiers

When `volume_ratio` is extreme, Telegram notifications append a suffix to the signal alert:

| Qualifier | Condition | Meaning |
|-----------|-----------|---------|
| 📈 volume surge | `volume_ratio ≥ 1.5` | Confirms conviction — capitulation selling (for buy signals) or blow-off top (for sell signals) |
| 📉 thin volume | `volume_ratio ≤ 0.5` | Weakens conviction — price moves on low volume are less reliable |

> **Note:** Volume qualifiers appear in Telegram notifications only. They do NOT change the signal enum value. `THESIS_BROKEN` never receives a volume qualifier (fundamental signal, volume irrelevant).

### None Handling

When technical data is unavailable (e.g., Cash category stocks skip yfinance signals):
- RSI = None: P2, P4, P4.5, P6 (RSI part), P7 conditions are skipped
- Bias = None: P2, P3, P4.5, P5, P6 (bias part), P7 conditions are skipped
- bias_200 = None: Phase 2 MA200 amplifier is skipped entirely
- Both None: only `THESIS_BROKEN` (P1) or `NORMAL` (P8) are reachable

## Market Sentiment (5-Tier)

Market sentiment is determined by the percentage of **Trend Setter** stocks trading below their 60-day moving average. It serves as a contextual backdrop — it does NOT gate signal logic.

| % Below 60MA | Sentiment | Icon | Guidance |
|--------------|-----------|------|----------|
| 0–10% | `STRONG_BULLISH` | ☀️ | Nearly all trend setters healthy — strong breadth, full risk-on |
| 10–30% | `BULLISH` | 🌤️ | Mostly healthy — normal accumulation conditions |
| 30–50% | `NEUTRAL` | ⛅ | Mixed breadth — transition zone, be selective |
| 50–70% | `BEARISH` | 🌧️ | Majority weakening — reduce exposure, tighten stops |
| >70% | `STRONG_BEARISH` | ⛈️ | Extreme weakness — defensive posture, cash is king |

The `GET /scan/last` endpoint returns the current sentiment in `market_sentiment.status` (e.g., `"BULLISH"`) and `market_sentiment.below_60ma_pct`.

## Service Operations

Use `exec` tool to run these commands from the Folio project root for infrastructure management.

### Backup & Restore

- `make backup` — Backup database (timestamped file in `./backups/`)
- `make restore` — Restore from latest backup
- `make restore FILE=backups/radar-YYYYMMDD.db` — Restore specific backup

### Upgrade & Restart

When code changes have been pushed to the repository, follow this workflow to apply them to the running service:

| Step | Command | Purpose |
|------|---------|---------|
| 1. Pull latest code | `git pull origin main` | Fetch code changes (or use current branch name) |
| 2. Rebuild & restart | `make up` | Rebuild images with changes and restart containers (zero downtime, data preserved) |
| 3. Verify health | `curl -sf http://localhost:8000/health` | Backend health check |
| 4. Check status | `docker compose ps` | Verify all containers are running |
| 5. Troubleshoot (if needed) | `docker compose logs backend --tail 50` | View recent logs if health check fails |


### Health & Diagnostics

- `curl -sf http://localhost:8000/health` — Backend health check
- `docker compose ps` — Container status
- `docker compose logs backend --tail 50` — Recent backend logs
