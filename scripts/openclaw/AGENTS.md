# Folio — OpenClaw Workspace Instructions

## System Context

You have access to **Folio (智能資產配置)**, a self-hosted stock tracking and market scanning system. It runs as a Docker Compose application with a FastAPI backend at `http://localhost:8000`.

## How to Interact

Use the `exec` tool with `curl` to call the Folio API:

```bash
# Quick portfolio overview (plain text)
curl -s http://localhost:8000/summary

# Structured command via webhook
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action": "signals", "ticker": "NVDA"}'
```

## Key Endpoints

### Primary (use these first)

- **`GET /summary`** — Plain-text portfolio health overview. Start here.
- **`POST /webhook`** — Single structured entry point for all actions. Accepts `{"action": "...", "ticker": "...", "params": {}}`.

### Webhook Actions

| Action | What it does |
|--------|-------------|
| `help` | List all supported actions and their parameters (self-discovery) |
| `summary` | Portfolio health + stock list |
| `signals` | Technical indicators for a ticker (RSI, MA, Bias) |
| `scan` | Trigger background full scan (results via Telegram) |
| `moat` | Gross margin YoY analysis for a ticker |
| `alerts` | List price alerts for a ticker |
| `fear_greed` | Fear & Greed Index (VIX + CNN composite score) |
| `add_stock` | Add stock with `params: {ticker, category, thesis, tags}` |
| `withdraw` | Smart withdrawal plan with `params: {amount, currency}` |
| `fx_watch` | Check FX exchange timing alerts & send Telegram notifications (monitors custom currency pairs with cooldown) |

> **Start with `help`** — call `POST /webhook {"action": "help"}` to discover all available actions at runtime.

### Direct API (for advanced queries)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/stocks` | All tracked stocks |
| `GET` | `/stocks/export` | Export watchlist as JSON |
| `POST` | `/ticker` | Add new stock |
| `GET` | `/ticker/{ticker}/signals` | Technical signals |
| `GET` | `/ticker/{ticker}/moat` | Moat analysis |
| `POST` | `/ticker/{ticker}/thesis` | Update thesis |
| `PATCH` | `/ticker/{ticker}/category` | Switch category |
| `GET` | `/ticker/{ticker}/scan-history` | Scan history |
| `GET` | `/ticker/{ticker}/alerts` | Price alerts |
| `POST` | `/ticker/{ticker}/alerts` | Create price alert |
| `GET` | `/ticker/{ticker}/earnings` | Earnings calendar |
| `GET` | `/ticker/{ticker}/dividend` | Dividend info |
| `POST` | `/scan` | Trigger scan |
| `POST` | `/digest` | Trigger weekly digest |
| `GET` | `/personas/templates` | Investment persona templates |
| `GET` | `/profiles` | Active investment profile |
| `POST` | `/profiles` | Create investment profile |
| `GET` | `/holdings` | All holdings |
| `POST` | `/holdings` | Add holding |
| `GET` | `/rebalance` | Rebalance analysis |
| `GET` | `/settings/telegram` | Telegram notification settings |
| `PUT` | `/settings/telegram` | Update Telegram settings (dual-mode) |
| `POST` | `/settings/telegram/test` | Send a test Telegram message |
| `GET` | `/settings/preferences` | User preferences (privacy mode, etc.) |
| `PUT` | `/settings/preferences` | Update user preferences (upsert) |
| `GET` | `/market/fear-greed` | Fear & Greed Index (VIX + CNN composite) |
| `GET` | `/scan/last` | Last scan timestamp + market sentiment + F&G |
| `GET` | `/currency-exposure` | Currency exposure analysis with `cash_breakdown` + `breakdown` + `fx_rate_alerts` (three-tier), FX movements, risk level |
| `POST` | `/currency-exposure/alert` | Trigger FX exposure Telegram alert — three-tier detection (daily >1.5%, 5-day >2%, 3-month >8%), includes cash exposure amounts |
| `GET` | `/fx-watch` | Get all FX watch configs (supports `?active_only=true`) |
| `POST` | `/fx-watch` | Create FX watch config (base_currency, quote_currency, recent_high_days, consecutive_increase_days, alert_on_recent_high, alert_on_consecutive_increase, reminder_interval_hours) |
| `PATCH` | `/fx-watch/{id}` | Update FX watch config (optional fields) |
| `DELETE` | `/fx-watch/{id}` | Delete FX watch config |
| `POST` | `/fx-watch/check` | Check all FX watches (analysis only, no Telegram) |
| `POST` | `/fx-watch/alert` | Check FX watches & send Telegram alerts (with per-watch cooldown) |
| `POST` | `/withdraw` | Smart withdrawal plan (Liquidity Waterfall) |

### Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Error Handling

Direct API errors return structured JSON with a machine-readable `error_code`:

```json
{"detail": {"error_code": "STOCK_NOT_FOUND", "detail": "找不到股票 NVDA。"}}
```

Branch on `error_code` (not the human-readable `detail` string). Common codes:
- `STOCK_NOT_FOUND` / `STOCK_ALREADY_EXISTS` / `STOCK_ALREADY_INACTIVE` / `STOCK_ALREADY_ACTIVE`
- `CATEGORY_UNCHANGED` / `HOLDING_NOT_FOUND` / `PROFILE_NOT_FOUND`
- `SCAN_IN_PROGRESS` / `DIGEST_IN_PROGRESS`
- `TELEGRAM_NOT_CONFIGURED` / `TELEGRAM_SEND_FAILED`
- `PREFERENCES_UPDATE_FAILED`

## Response Guidelines

- Be concise — the user wants quick investment insights, not essays
- When asked about market sentiment or timing, call `/webhook` with `fear_greed` to get the VIX + CNN Fear & Greed composite
- When asked "which stock should I sell?" or "I need cash", call `/webhook` with `withdraw` and the target amount/currency
- When asked about portfolio status, call `/summary` first
- When asked about a specific stock, call `/webhook` with `signals` or `moat`
- Present data in a structured, readable format
- Use the stock categories to contextualize advice:
  - **Trend_Setter (風向球)**: Market direction indicators
  - **Moat (護城河)**: Companies with competitive advantages
  - **Growth (成長夢想)**: High-volatility growth stocks
  - **Bond (債券)**: Bonds and fixed-income ETFs
  - **Cash (現金)**: Idle cash positions
