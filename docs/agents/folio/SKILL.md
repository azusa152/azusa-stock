---
name: folio
description: Self-hosted investment tracking for stocks, portfolio, holdings, FX monitoring, and guru 13F analysis. Use when asked about portfolio status, watchlist, stock signals, market sentiment, price alerts, FX exchange timing, moat analysis, stress test, smart withdrawal, or superinvestor positions. Supports US/JP/TW/HK markets. Backend must be running at http://localhost:8000.
homepage: http://localhost:8000/docs
metadata: { "openclaw": { "requires": { "bins": ["docker", "curl"] }, "emoji": "📊" } }
---

# Folio Skill

Folio is a self-hosted investment analysis system. Use the `exec` tool with `curl` to interact with the FastAPI backend at `http://localhost:8000`.

> **Start here:** `POST /webhook {"action": "help"}` — self-discovers all available actions at runtime.

## Prerequisites

- Docker Compose services running (`make up` from project root)
- Backend at `http://localhost:8000`
- Set `FOLIO_API_KEY` env var for production; omit for dev (auth disabled by default)

## Authentication

Include `-H "X-API-Key: $FOLIO_API_KEY"` on all requests when auth is enabled.

```bash
make generate-key                           # generate key
echo "FOLIO_API_KEY=your-key" >> .env       # persist
export FOLIO_API_KEY="your-key"             # current shell
```

## Language (i18n)

Folio supports 4 languages: `zh-TW` (default), `en`, `ja`, `zh-CN`. Change via `PUT /settings/preferences` with `{"language": "en"}`. All API responses and Telegram notifications are localized. Always branch on `error_code`, not the `detail` string.

## Quick Start

```bash
# Portfolio overview
curl -s http://localhost:8000/summary -H "X-API-Key: $FOLIO_API_KEY"

# Webhook (preferred entry point)
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action": "signals", "ticker": "NVDA"}'
```

## Webhook Actions

`POST /webhook` — body: `{"action": "...", "ticker": "...", "params": {}}`

| Action | Description | Example |
|--------|-------------|---------|
| `help` | List all actions + params at runtime | `{"action": "help"}` |
| `summary` | Portfolio health overview | `{"action": "summary"}` |
| `signals` | Technical indicators (RSI/MA/Bias) | `{"action": "signals", "ticker": "NVDA"}` |
| `scan` | Full scan (background + Telegram) | `{"action": "scan"}` |
| `moat` | Gross margin YoY analysis | `{"action": "moat", "ticker": "TSM"}` |
| `alerts` | List price alerts for a ticker | `{"action": "alerts", "ticker": "AAPL"}` |
| `fear_greed` | Fear & Greed Index (VIX + CNN) | `{"action": "fear_greed"}` |
| `add_stock` | Add stock to watchlist | `{"action": "add_stock", "params": {"ticker": "AMD", "category": "Moat", "thesis": "...", "tags": ["AI"]}}` |
| `withdraw` | Smart withdrawal plan | `{"action": "withdraw", "params": {"amount": 50000, "currency": "TWD"}}` |
| `fx_watch` | Check FX timing + send Telegram alerts | `{"action": "fx_watch"}` |

Webhook response envelope: `{"success": true, "message": "...", "data": {}}`

## Key Direct API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/summary` | Rich plain-text portfolio overview |
| `GET` | `/stocks` | All tracked stocks with `last_scan_signal` |
| `POST` | `/ticker` | Add stock |
| `GET` | `/ticker/{ticker}/signals` | Signals incl. `bias_percentile`, `is_rogue_wave` |
| `GET` | `/ticker/{ticker}/moat` | Moat analysis |
| `POST` | `/ticker/{ticker}/alerts` | Create price alert |
| `PATCH` | `/alerts/{alert_id}/toggle` | Pause/resume alert |
| `GET` | `/rebalance` | Rebalance + X-Ray; add `?display_currency=TWD` |
| `GET` | `/stress-test` | Crash simulation (`?scenario_drop_pct=-20`) |
| `GET` | `/currency-exposure` | Currency risk + three-tier FX alerts |
| `POST` | `/fx-watch` | Create FX watch config |
| `POST` | `/fx-watch/check` | Analyze FX watches (no Telegram) |
| `POST` | `/fx-watch/alert` | Analyze + send Telegram (with cooldown) |
| `GET` | `/holdings` | All holdings |
| `POST` | `/holdings` | Add holding (auto-snapshots FX rate) |
| `POST` | `/withdraw` | Smart withdrawal (Liquidity Waterfall) |
| `GET` | `/snapshots/twr` | Time-weighted return (YTD default) |
| `GET` | `/scan/last` | Last scan timestamp + market sentiment |
| `GET` | `/market/fear-greed` | Fear & Greed Index |
| `GET` | `/gurus` | Tracked superinvestors |
| `POST` | `/gurus/sync` | Batch-sync all guru 13F filings |
| `GET` | `/gurus/{id}/holdings` | Holdings with action labels; add `?include_performance=true` |
| `GET` | `/gurus/{id}/qoq` | Quarter-over-quarter history (`?quarters=4`) |
| `GET` | `/resonance` | Guru overlap with your watchlist/holdings |
| `PUT` | `/settings/preferences` | Update language (`zh-TW`/`en`/`ja`/`zh-CN`) |

> Full endpoint list with field specs and query params: read `{baseDir}/reference.md`.

## Error Handling

Direct API errors: `{"detail": {"error_code": "STOCK_NOT_FOUND", "detail": "..."}}`

Branch on `error_code` — `detail` is localized and must not be parsed.

Common codes: `STOCK_NOT_FOUND` · `STOCK_ALREADY_EXISTS` · `HOLDING_NOT_FOUND` · `SCAN_IN_PROGRESS` · `TELEGRAM_NOT_CONFIGURED` · `PREFERENCES_UPDATE_FAILED`

## Categories

| Category | Label | Description |
|----------|-------|-------------|
| `Trend_Setter` | 🌊 風向球 | Market ETFs, megacaps |
| `Moat` | 🏰 護城河 | Durable competitive advantage |
| `Growth` | 🚀 成長夢想 | High-volatility growth |
| `Bond` | 🛡️ 債券 | Fixed-income ETFs |
| `Cash` | 💵 現金 | Idle cash |

RSI thresholds are category-aware: Growth +2, Moat +1, Bond −3 offsets applied to all thresholds.

## Signal Quick Reference

| Signal | Icon | Meaning |
|--------|------|---------|
| `THESIS_BROKEN` | 🚨 | Fundamental thesis broken — re-evaluate holding |
| `DEEP_VALUE` | 💎 | Both price + momentum confirm deep discount — high-conviction entry |
| `OVERSOLD` | 📉 | Extreme price low, RSI not confirming — watch for confirmation |
| `CONTRARIAN_BUY` | 🟢 | RSI oversold, price not overheated — potential entry |
| `APPROACHING_BUY` | 🎯 | Accumulation zone — approaching buy range |
| `OVERHEATED` | 🔥 | Both indicators overheated — sell warning, avoid chasing |
| `CAUTION_HIGH` | ⚠️ | Single indicator elevated — reduce new positions |
| `WEAKENING` | 🔻 | Early weakness — monitor closely |
| `NORMAL` | ➖ | No notable signal |

When `is_rogue_wave: true`: bias is at P95+ historically with volume surge — party is likely peaking; avoid leveraged chasing.

> Full signal conditions, MA200 amplifier logic, volume qualifiers, market sentiment thresholds (US/JP/TW): read `{baseDir}/reference.md`.

## Essential Tips

- Call `summary` first — returns total value, daily change, active signals, drift warnings, Smart Money in one call
- Add `?display_currency=TWD` to `/rebalance` for multi-currency display (USD/TWD/JPY/EUR/GBP/CNY/HKD/SGD/THB)
- When adding non-USD holdings, set `currency` field — FX rate is auto-snapshotted as `purchase_fx_rate` for FX return tracking
- Use `POST /fx-watch/check` for silent FX analysis; `POST /fx-watch/alert` when ready to send Telegram (subject to per-watch cooldown)
- Use `GET /gurus/{id}/qoq?quarters=4` to detect conviction builds (`increasing` trend) vs exits (`exited`)
- Add `?include_performance=true` to guru holdings for price performance since SEC filing date
- Use `GET /resonance` for full guru × watchlist overlap matrix; `GET /resonance/{ticker}` to find who holds a specific stock
- Use `PATCH /alerts/{id}/toggle` to silently pause alerts during earnings seasons
- Run `make backup` before any destructive operation (e.g., `docker compose down -v`)
- Check `docker compose logs backend --tail 50` first when users report errors after an upgrade
