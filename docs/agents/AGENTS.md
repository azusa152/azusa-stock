# Folio — OpenClaw Workspace Instructions

## System Context

You have access to **Folio (智能資產配置)**, a self-hosted stock tracking and market scanning system. It runs as a Docker Compose application with a FastAPI backend at `http://localhost:8000`.

## Authentication

Folio supports optional API key authentication via the `X-API-Key` header. When `FOLIO_API_KEY` is set in the environment, all API requests must include the key.

**Dev Mode (default):** If `FOLIO_API_KEY` is unset, authentication is disabled — no breaking changes for existing users.

**Production Mode:** Set `FOLIO_API_KEY` in `.env` and include the header in all requests:

```bash
# Generate a secure API key
make generate-key

# Add to .env
echo "FOLIO_API_KEY=your-generated-key" >> .env

# Use in requests
export FOLIO_API_KEY="your-generated-key"
curl -s http://localhost:8000/summary \
  -H "X-API-Key: $FOLIO_API_KEY"
```

## Language (i18n)

Folio supports 4 languages: `zh-TW` (default), `en`, `ja`, `zh-CN`. All API response messages and Telegram notifications are localized based on the user's preference stored via `PUT /settings/preferences` with `{"language": "en"}`. The `detail` field in error responses varies by language -- always branch on `error_code`, not the human-readable string.

## How to Interact

Use the `exec` tool with `curl` to call the Folio API:

```bash
# Quick portfolio overview (plain text)
# Add -H "X-API-Key: $FOLIO_API_KEY" if auth is enabled
curl -s http://localhost:8000/summary

# Structured command via webhook
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action": "signals", "ticker": "NVDA"}'
```

## Key Endpoints

### Primary (use these first)

- **`GET /summary`** — Rich plain-text portfolio overview. Start here. Includes: total value + daily change %, category groups, active signals, top 3 movers, allocation drift warnings, Smart Money highlights.
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
| `GET` | `/stocks` | All tracked stocks (includes `last_scan_signal` — persisted signal from last full scan) |
| `GET` | `/stocks/export` | Export watchlist as JSON |
| `POST` | `/ticker` | Add new stock |
| `GET` | `/ticker/{ticker}/signals` | Technical signals (includes `bias_percentile` and `is_rogue_wave` for Rogue Wave detection) |
| `GET` | `/ticker/{ticker}/moat` | Moat analysis |
| `POST` | `/ticker/{ticker}/thesis` | Update thesis |
| `PATCH` | `/ticker/{ticker}/category` | Switch category |
| `GET` | `/ticker/{ticker}/scan-history` | Scan history |
| `GET` | `/ticker/{ticker}/alerts` | Price alerts |
| `POST` | `/ticker/{ticker}/alerts` | Create price alert |
| `PATCH` | `/alerts/{alert_id}/toggle` | Toggle alert on/off (active ↔ paused) |
| `DELETE` | `/alerts/{alert_id}` | Delete price alert |
| `GET` | `/ticker/{ticker}/earnings` | Earnings calendar |
| `GET` | `/ticker/{ticker}/dividend` | Dividend info |
| `POST` | `/scan` | Trigger scan |
| `POST` | `/digest` | Trigger weekly digest |
| `GET` | `/snapshots` | Historical portfolio snapshots — `?days=30` (1–730) or `?start=YYYY-MM-DD&end=YYYY-MM-DD` |
| `GET` | `/snapshots/twr` | Time-weighted return — `?start=&end=` (defaults to YTD); `twr_pct` is null when < 2 snapshots |
| `POST` | `/snapshots/take` | Trigger today's portfolio snapshot (background, upsert) |
| `GET` | `/personas/templates` | Investment persona templates |
| `GET` | `/profiles` | Active investment profile |
| `POST` | `/profiles` | Create investment profile |
| `GET` | `/holdings` | All holdings |
| `POST` | `/holdings` | Add holding |
| `GET` | `/rebalance` | Rebalance analysis |
| `GET` | `/stress-test` | Stress test analysis (portfolio crash simulation) |
| `GET` | `/settings/telegram` | Telegram notification settings |
| `PUT` | `/settings/telegram` | Update Telegram settings (dual-mode) |
| `POST` | `/settings/telegram/test` | Send a test Telegram message |
| `GET` | `/settings/preferences` | User preferences (language, privacy mode, etc.) |
| `PUT` | `/settings/preferences` | Update user preferences (upsert) -- supports `language` field (`zh-TW`/`en`/`ja`/`zh-CN`) |
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
| `GET` | `/gurus` | List all tracked gurus (id, name, display_name, cik) |
| `POST` | `/gurus` | Add custom guru — body: `{"name": "Berkshire Hathaway Inc", "cik": "0001067983", "display_name": "Warren Buffett"}` |
| `DELETE` | `/gurus/{guru_id}` | Deactivate guru (history preserved) |
| `POST` | `/gurus/sync` | Batch-sync all gurus' 13F filings from SEC EDGAR (mutex-protected, safe to call from cron) |
| `POST` | `/gurus/{guru_id}/sync` | Sync one guru's 13F — returns `{"status": "synced"\|"skipped", "message": "..."}` |
| `GET` | `/gurus/{guru_id}/filing` | Latest 13F filing summary: report_date, filing_date, total_value, holdings_count, new_positions, sold_out, increased, decreased |
| `GET` | `/gurus/{guru_id}/holdings` | All holdings with action labels (NEW_POSITION/SOLD_OUT/INCREASED/DECREASED/UNCHANGED), ticker, value, shares, change_pct, weight_pct |
| `GET` | `/gurus/{guru_id}/top` | Top N holdings by weight — supports `?n=10` |
| `GET` | `/resonance` | Portfolio resonance overview — all guru overlaps with your watchlist/holdings. Returns `{results: [{guru_display_name, overlapping_tickers, overlap_count, holdings: [{ticker, action, weight_pct}]}], total_gurus, gurus_with_overlap}` |
| `GET` | `/resonance/{ticker}` | Which gurus hold a specific ticker and their current action |

### Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Error Handling

Direct API errors return structured JSON with a machine-readable `error_code`:

```json
{"detail": {"error_code": "STOCK_NOT_FOUND", "detail": "找不到股票 NVDA。"}}
```

Branch on `error_code` (not the human-readable `detail` string, which is localized based on user language preference). Common codes:
- `STOCK_NOT_FOUND` / `STOCK_ALREADY_EXISTS` / `STOCK_ALREADY_INACTIVE` / `STOCK_ALREADY_ACTIVE`
- `CATEGORY_UNCHANGED` / `HOLDING_NOT_FOUND` / `PROFILE_NOT_FOUND`
- `SCAN_IN_PROGRESS` / `DIGEST_IN_PROGRESS`
- `TELEGRAM_NOT_CONFIGURED` / `TELEGRAM_SEND_FAILED`
- `PREFERENCES_UPDATE_FAILED`

## Service Operations

Folio provides `make` targets for service management. Use `exec` to run these from the project root.

### Backup & Restore

| Command | Description |
|---------|-------------|
| `make backup` | Backup database to `./backups/radar-YYYYMMDD_HHMMSS.db` |
| `make restore` | Restore from the latest backup in `./backups/` |
| `make restore FILE=backups/radar-20260214.db` | Restore from a specific backup file |

### Upgrade & Restart

When code changes have been pushed to the repository, follow this workflow to apply them to the running service:

| Step | Command | Purpose |
|------|---------|---------|
| 1. Pull latest code | `git pull origin main` | Fetch code changes (or use current branch name) |
| 2. Rebuild & restart | `make up` | Rebuild images with changes and restart containers (zero downtime, data preserved) |
| 3. Verify health | `curl -sf http://localhost:8000/health` | Backend health check |
| 4. Check status | `docker compose ps` | Verify all containers are running |
| 5. Troubleshoot (if needed) | `docker compose logs backend --tail 50` | View recent logs if health check fails |

| Command | Description |
|---------|-------------|
| `docker compose down -v` | Full reset -- DELETES ALL DATA (use `make backup` first!) |

### Health Check

| Command | Description |
|---------|-------------|
| `curl -sf http://localhost:8000/health` | Backend health check |
| `docker compose ps` | Check container status |
| `docker compose logs backend --tail 50` | View recent backend logs |

## Response Guidelines

- Be concise — the user wants quick investment insights, not essays
- When a `signals` response has `is_rogue_wave: true`, warn the user: bias is at a 3-year extreme (≥ P95) with volume surge — the party is likely peaking; avoid leveraged chasing
- When asked about market sentiment or timing, call `/webhook` with `fear_greed` to get the VIX + CNN Fear & Greed composite
- When asked "which stock should I sell?" or "I need cash", call `/webhook` with `withdraw` and the target amount/currency
- When asked about portfolio status, call `/summary` first — it returns total value + daily change, category groups, active signals, top movers, drift warnings, and Smart Money highlights in one plain-text response
- When asked about a specific stock, call `/webhook` with `signals` or `moat`; interpret the `last_scan_signal` value using the **Signal Reference** section below
- When asked "which gurus hold this stock?" or "what are the big names buying?", call `GET /resonance` to get the full overlap matrix
- Use `PATCH /alerts/{alert_id}/toggle` to pause or resume a price alert without deleting it — useful for silencing alerts during earnings season or known volatile periods
- When asked to sync the latest 13F data, call `POST /gurus/sync` (all gurus) or `POST /gurus/{id}/sync` (one guru); status `"synced"` = new data, `"skipped"` = already current
- Present data in a structured, readable format

## Signal Reference

Folio uses two signal fields per stock:

- **`last_scan_signal`** — persisted result of the last full scan (moat + RSI + bias). Returned by `GET /stocks` and `GET /summary`.
- **`computed_signal`** — real-time signal recomputed on each request from live RSI/bias (no moat check). Returned by `GET /stocks/enriched`. The dashboard Signal Alerts section and radar page both prefer `computed_signal` when available, falling back to `last_scan_signal`. `THESIS_BROKEN` is always taken from the persisted value (moat analysis is required to set it).

Both fields use the same 8-state taxonomy:

| Signal | Icon | Condition | What to tell the user |
|--------|------|-----------|----------------------|
| `THESIS_BROKEN` | 🔴 | Gross margin YoY deteriorated >2pp | Fundamental thesis broken — recommend re-evaluating the holding |
| `DEEP_VALUE` | 🔵 | Bias < −20% AND RSI < 35 | Both price and momentum confirm deep discount — high-conviction entry zone |
| `OVERSOLD` | 🟣 | Bias < −20% (RSI ≥ 35) | Price at extreme low; RSI not yet confirming — watch for further confirmation |
| `CONTRARIAN_BUY` | 🟢 | RSI < 35 AND Bias < 20% | RSI oversold, price not overheated — potential contrarian entry |
| `OVERHEATED` | 🟠 | Bias > 20% AND RSI > 70 | Both indicators overheated — sell warning, avoid chasing |
| `CAUTION_HIGH` | 🟡 | Bias > 20% OR RSI > 70 | Single indicator elevated — reduce new positions |
| `WEAKENING` | 🟤 | Bias < −15% AND RSI < 38 | Early weakness, not yet extreme — monitor closely |
| `NORMAL` | ⚪ | Everything else | No notable signal |

Telegram notifications may append volume context: **📈 volume surge** (`volume_ratio ≥ 1.5`) strengthens conviction; **📉 thin volume** (`volume_ratio ≤ 0.5`) weakens it. These qualifiers do not change the signal enum.

## Categories

- Use the stock categories to contextualize advice:
  - **Trend_Setter (風向球)**: Market direction indicators
  - **Moat (護城河)**: Companies with competitive advantages
  - **Growth (成長夢想)**: High-volatility growth stocks
  - **Bond (債券)**: Bonds and fixed-income ETFs
  - **Cash (現金)**: Idle cash positions
