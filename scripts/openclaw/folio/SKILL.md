---
name: folio
description: Folio 智能資產配置 — 股票追蹤、掃描與警報系統
version: 1.0.0
---

# Folio Skill

Folio 是一套自架的投資追蹤系統，提供股票觀察名單管理、三層漏斗掃描、護城河分析、價格警報、以及 Telegram 通知。

## Prerequisites

- Folio 的 Docker Compose 服務正在運行
- Backend API 預設在 `http://localhost:8000`

## Quick Start

### 查看投資組合摘要

```bash
curl -s http://localhost:8000/summary
```

### 透過 Webhook 執行操作

```bash
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
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
| `summary` | 投資組合健康摘要 | No | `{"action": "summary"}` |
| `signals` | 單一股票技術指標 | Yes | `{"action": "signals", "ticker": "NVDA"}` |
| `scan` | 觸發全域掃描（背景執行） | No | `{"action": "scan"}` |
| `moat` | 護城河分析（毛利率 YoY） | Yes | `{"action": "moat", "ticker": "TSM"}` |
| `alerts` | 查看價格警報 | Yes | `{"action": "alerts", "ticker": "AAPL"}` |
| `add_stock` | 新增股票到觀察名單 | Yes (in params) | See below |

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

### Response Format

All webhook responses follow this structure:

```json
{
  "success": true,
  "message": "Human-readable result",
  "data": {}
}
```

## Direct API Endpoints

For advanced use, you can call individual endpoints directly:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/summary` | 純文字投資組合摘要 |
| `GET` | `/stocks` | 所有追蹤中股票清單 |
| `GET` | `/stocks/export` | 匯出觀察名單 (JSON) |
| `POST` | `/ticker` | 新增股票 |
| `GET` | `/ticker/{ticker}/signals` | 技術訊號 (RSI, MA, Bias) |
| `GET` | `/ticker/{ticker}/moat` | 護城河分析 |
| `POST` | `/ticker/{ticker}/thesis` | 更新觀點 |
| `PATCH` | `/ticker/{ticker}/category` | 切換分類 |
| `POST` | `/scan` | 觸發全域掃描 |
| `POST` | `/digest` | 觸發每週摘要 |
| `GET` | `/ticker/{ticker}/scan-history` | 掃描歷史 |
| `GET` | `/ticker/{ticker}/alerts` | 價格警報清單 |
| `POST` | `/ticker/{ticker}/alerts` | 建立價格警報 |
| `GET` | `/ticker/{ticker}/earnings` | 財報日曆 |
| `GET` | `/ticker/{ticker}/dividend` | 股息資訊 |
| `GET` | `/personas/templates` | 投資人格範本列表 |
| `GET` | `/profiles` | 目前啟用的投資組合配置 |
| `POST` | `/profiles` | 建立投資組合配置 |
| `GET` | `/holdings` | 所有持倉 |
| `POST` | `/holdings` | 新增持倉（含可選 broker / currency 欄位，currency 預設 USD） |
| `POST` | `/holdings/cash` | 新增現金持倉 |
| `GET` | `/rebalance` | 再平衡分析，支援 `?display_currency=TWD` 指定顯示幣別（自動匯率換算） |
| `GET` | `/settings/telegram` | Telegram 通知設定（token 遮蔽） |
| `PUT` | `/settings/telegram` | 更新 Telegram 通知設定（雙模式） |
| `POST` | `/settings/telegram/test` | 發送 Telegram 測試訊息 |
| `GET` | `/docs` | Swagger UI (互動式 API 文件) |
| `GET` | `/openapi.json` | OpenAPI 規範 |

## Categories

| Category | Label | Description |
|----------|-------|-------------|
| `Trend_Setter` | 🌊 風向球 | 大盤 ETF、巨頭 |
| `Moat` | 🏰 護城河 | 不可替代的賣鏟子公司 |
| `Growth` | 🚀 成長夢想 | 高波動成長股 |
| `Bond` | 🛡️ 債券 | 國債、投資等級債券 ETF |
| `Cash` | 💵 現金 | 閒置現金 |

## Usage Tips

- Use `summary` first to get an overview before drilling into individual stocks
- Use `signals` to check if a stock is oversold (RSI < 30) or overheated (Bias > 20%)
- Use `moat` to verify if a stock's fundamentals (gross margin) are still intact
- Use `scan` to trigger a full portfolio analysis with Telegram notifications
- Use `rebalance` to check if portfolio allocation drifts from target
- Add `?display_currency=TWD` to `/rebalance` to see all values in TWD (supports USD, TWD, JPY, EUR, GBP, CNY, HKD, SGD, THB)
- When adding holdings, set `currency` field to match the holding's native currency (e.g., "TWD" for Taiwan stocks, "JPY" for Japan stocks)
