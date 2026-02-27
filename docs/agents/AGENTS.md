# Folio — OpenClaw Workspace Instructions

## System Context

You have access to **Folio (智能資產配置)**, a self-hosted stock tracking and market scanning system. It runs as a Docker Compose application with a FastAPI backend at `http://localhost:8000`.

## Authentication

Folio supports optional API key authentication via the `X-API-Key` header. When `FOLIO_API_KEY` is set in the environment, all API requests must include the key.

**Dev Mode (default):** If `FOLIO_API_KEY` is unset, authentication is disabled.

**Production Mode:** Set `FOLIO_API_KEY` in `.env` and include the header in all requests:

```bash
make generate-key
echo "FOLIO_API_KEY=your-generated-key" >> .env
export FOLIO_API_KEY="your-generated-key"
curl -s http://localhost:8000/summary -H "X-API-Key: $FOLIO_API_KEY"
```

## Language (i18n)

Folio supports 4 languages: `zh-TW` (default), `en`, `ja`, `zh-CN`. All API response messages and Telegram notifications are localized based on the user's preference stored via `PUT /settings/preferences` with `{"language": "en"}`. The `detail` field in error responses varies by language — always branch on `error_code`, not the human-readable string.

## How to Interact

Use the `exec` tool with `curl` to call the Folio API:

```bash
# Quick portfolio overview (plain text)
curl -s http://localhost:8000/summary

# Structured command via webhook
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action": "signals", "ticker": "NVDA"}'
```

## Key Endpoints

### Primary (use these first)

- **`GET /summary`** — Rich plain-text portfolio overview: total value + daily change %, category groups, active signals, top 3 movers, allocation drift warnings, Smart Money highlights.
- **`POST /webhook`** — Single entry point for all actions. Accepts `{"action": "...", "ticker": "...", "params": {}}`.

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
| `fx_watch` | Check FX exchange timing alerts & send Telegram notifications |

> **Start with `help`** — call `POST /webhook {"action": "help"}` to discover all available actions at runtime.

### Direct API (most-used)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/stocks` | All tracked stocks (includes `last_scan_signal`) |
| `POST` | `/ticker` | Add new stock |
| `GET` | `/ticker/{ticker}/signals` | Technical signals (includes `bias_percentile` and `is_rogue_wave`) |
| `GET` | `/ticker/{ticker}/moat` | Moat analysis |
| `POST` | `/ticker/{ticker}/alerts` | Create price alert |
| `PATCH` | `/alerts/{alert_id}/toggle` | Toggle alert on/off (active / paused) |
| `GET` | `/rebalance` | Rebalance + X-Ray; add `?display_currency=TWD` |
| `GET` | `/stress-test` | Stress test (portfolio crash simulation) |
| `GET` | `/currency-exposure` | Currency exposure with `fx_rate_alerts` (three-tier) |
| `POST` | `/fx-watch` | Create FX watch config |
| `POST` | `/fx-watch/check` | Analyze FX watches (no Telegram) |
| `POST` | `/fx-watch/alert` | Analyze + send Telegram (with cooldown) |
| `GET` | `/holdings` | All holdings |
| `POST` | `/holdings` | Add holding (auto-snapshots `purchase_fx_rate`) |
| `POST` | `/withdraw` | Smart withdrawal (Liquidity Waterfall) |
| `GET` | `/snapshots/twr` | Time-weighted return (YTD default) |
| `GET` | `/scan/last` | Last scan timestamp + market sentiment + F&G |
| `GET` | `/market/fear-greed` | Fear & Greed Index (VIX + CNN composite) |
| `GET` | `/gurus` | Tracked superinvestors |
| `POST` | `/gurus/sync` | Batch-sync all guru 13F filings |
| `GET` | `/gurus/{id}/holdings` | Holdings with action labels; add `?include_performance=true` |
| `GET` | `/gurus/{id}/qoq` | Quarter-over-quarter history (`?quarters=4`) |
| `GET` | `/resonance` | Guru overlap with your watchlist/holdings |
| `PUT` | `/settings/preferences` | Update language (`zh-TW`/`en`/`ja`/`zh-CN`) |

If the `folio` skill is installed, read its bundled `reference.md` for the full endpoint list with field specs, query parameters, signal taxonomy, and market sentiment thresholds.

### Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Error Handling

Direct API errors return structured JSON with a machine-readable `error_code`:

```json
{"detail": {"error_code": "STOCK_NOT_FOUND", "detail": "找不到股票 NVDA。"}}
```

Branch on `error_code` (not the human-readable `detail` string, which is localized). Common codes:
- `STOCK_NOT_FOUND` / `STOCK_ALREADY_EXISTS` / `STOCK_ALREADY_INACTIVE` / `STOCK_ALREADY_ACTIVE`
- `CATEGORY_UNCHANGED` / `HOLDING_NOT_FOUND` / `PROFILE_NOT_FOUND`
- `SCAN_IN_PROGRESS` / `DIGEST_IN_PROGRESS`
- `TELEGRAM_NOT_CONFIGURED` / `TELEGRAM_SEND_FAILED`
- `PREFERENCES_UPDATE_FAILED`

## Service Operations

Run `make` commands from the project root using the `exec` tool.

| Command | Description |
|---------|-------------|
| `make backup` | Backup database (timestamped file in `./backups/`) |
| `make restore` | Restore from latest backup |
| `make up` | Rebuild images + restart containers (zero downtime) |
| `curl -sf http://localhost:8000/health` | Backend health check |
| `docker compose ps` | Container status |
| `docker compose logs backend --tail 50` | Recent backend logs |

> `docker compose down -v` — full reset, **DELETES ALL DATA**. Always `make backup` first.

## Response Guidelines

- Be concise — the user wants quick investment insights, not essays
- When `signals` returns `is_rogue_wave: true`, warn the user: bias is at a 3-year extreme (≥ P95) with volume surge — the party is likely peaking; avoid leveraged chasing
- When asked about market sentiment or timing, call `/webhook` with `fear_greed`. For JP market use Nikkei VI thresholds (≥35 extreme fear, <14 extreme greed); for TW market use TAIEX realized vol thresholds (>30% extreme fear, <10% extreme greed)
- When asked "which stock should I sell?" or "I need cash", call `/webhook` with `withdraw` and the target amount/currency
- When asked about portfolio status, call `/summary` first
- When asked about a specific stock, call `/webhook` with `signals` or `moat`; interpret the signal using the **Signal Reference** below
- When asked "which gurus hold this stock?" or "what are the big names buying?", call `GET /resonance`
- Use `PATCH /alerts/{alert_id}/toggle` to pause/resume a price alert without deleting it
- When asked to sync the latest 13F data, call `POST /gurus/sync` (all) or `POST /gurus/{id}/sync` (one)
- Present data in a structured, readable format

## Signal Reference

Folio uses two signal fields: `last_scan_signal` (persisted, from full scan with moat check) and `computed_signal` (real-time RSI/bias, no moat). `THESIS_BROKEN` always comes from the persisted value.

RSI thresholds are category-aware (Growth +2, Moat +1, Bond −3). A MA200 amplifier can upgrade signals when price is far from the 200-day MA.

| Signal | Icon | What to tell the user |
|--------|------|-----------------------|
| `THESIS_BROKEN` | 🚨 | Fundamental thesis broken — recommend re-evaluating the holding |
| `DEEP_VALUE` | 💎 | Both price and momentum confirm deep discount — high-conviction entry zone |
| `OVERSOLD` | 📉 | Price at extreme low; RSI not yet confirming — watch for further confirmation |
| `CONTRARIAN_BUY` | 🟢 | RSI oversold, price not overheated — potential contrarian entry |
| `APPROACHING_BUY` | 🎯 | Accumulation zone — approaching buy range; monitor for RSI confirmation |
| `OVERHEATED` | 🔥 | Both indicators overheated — sell warning, avoid chasing |
| `CAUTION_HIGH` | ⚠️ | Single indicator elevated — reduce new positions |
| `WEAKENING` | 🔻 | Early weakness, not yet extreme — monitor closely |
| `NORMAL` | ➖ | No notable signal |

Telegram notifications may append volume context: **📈 volume surge** (`volume_ratio ≥ 1.5`) strengthens conviction; **📉 thin volume** (`volume_ratio ≤ 0.5`) weakens it.

## Categories

| Category | Label | Description |
|----------|-------|-------------|
| `Trend_Setter` | 🌊 風向球 | Market direction indicators |
| `Moat` | 🏰 護城河 | Companies with competitive advantages |
| `Growth` | 🚀 成長夢想 | High-volatility growth stocks |
| `Bond` | 🛡️ 債券 | Bonds and fixed-income ETFs |
| `Cash` | 💵 現金 | Idle cash positions |
