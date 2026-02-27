# Folio Reference

Detailed reference for signal taxonomy, market sentiment thresholds, endpoint field specs, and service operations. Load this file when you need specifics beyond the quick reference in `SKILL.md`.

---

## Signal Taxonomy

Folio uses two signal fields per stock:

- **`last_scan_signal`** — persisted from the last full scan (moat + RSI + bias). Returned by `GET /stocks` and `GET /summary`.
- **`computed_signal`** — real-time from live RSI/bias (no moat check). Returned by `GET /stocks/enriched`. Dashboard and radar prefer this, falling back to `last_scan_signal`. `THESIS_BROKEN` always comes from the persisted value (requires moat analysis).

Both fields use the same 9-state cascade. Higher priority (lower P number) trumps lower when multiple conditions apply.

**Category-aware RSI offsets** — applied to all RSI thresholds (buy and sell): Growth +2, Moat +1, Trend_Setter 0, Bond −3, Cash 0.

**MA200 amplifier (Phase 2)** — after the cascade, if `bias_200` is available: upgrade WEAKENING→APPROACHING_BUY or APPROACHING_BUY→CONTRARIAN_BUY when `bias_200 < −15%`; upgrade CAUTION_HIGH→OVERHEATED when `bias_200 > +20%` (asymmetric due to positive market drift).

| Priority | Signal | Icon | Condition (default offset=0) | Meaning |
|----------|--------|------|------------------------------|---------|
| P1 | `THESIS_BROKEN` | 🚨 | Gross margin YoY deteriorated >2pp | Fundamental thesis broken — re-evaluate holding |
| P2 | `DEEP_VALUE` | 💎 | Bias < −20% AND RSI < 35 | Both indicators confirm deep discount — highest-conviction entry |
| P3 | `OVERSOLD` | 📉 | Bias < −20% (RSI ≥ 35) | Extreme price discount; RSI not confirming — watch for confirmation |
| P4 | `CONTRARIAN_BUY` | 🟢 | RSI < 35 AND Bias < 20% | RSI oversold, price not overheated — potential contrarian entry |
| P4.5 | `APPROACHING_BUY` | 🎯 | RSI < 37 AND Bias < −15% | Accumulation zone — approaching buy range; monitor for RSI confirmation |
| P5 | `OVERHEATED` | 🔥 | Bias > 20% AND RSI > 70 | Both overheated — highest-conviction sell warning |
| P6 | `CAUTION_HIGH` | ⚠️ | Bias > 20% OR RSI > 70 | Single indicator elevated — reduce new positions, tighten stops |
| P7 | `WEAKENING` | 🔻 | Bias < −15% AND RSI < 38 | Early weakness — monitor closely |
| P8 | `NORMAL` | ➖ | Everything else | No notable signal |

### Volume Confidence Qualifiers

Appended to Telegram notifications only — do NOT change the signal enum value.

| Qualifier | Condition | Meaning |
|-----------|-----------|---------|
| 📈 volume surge | `volume_ratio ≥ 1.5` | Confirms conviction — capitulation selling (buy) or blow-off top (sell) |
| 📉 thin volume | `volume_ratio ≤ 0.5` | Weakens conviction — price moves on low volume are less reliable |

`THESIS_BROKEN` never receives a volume qualifier.

### None Handling

When technical data is unavailable (e.g., Cash category stocks skip yfinance signals):

- RSI = None: P2, P4, P4.5, P6 (RSI part), P7 conditions are skipped
- Bias = None: P2, P3, P4.5, P5, P6 (bias part), P7 conditions are skipped
- `bias_200` = None: Phase 2 MA200 amplifier is skipped entirely
- Both None: only `THESIS_BROKEN` (P1) or `NORMAL` (P8) are reachable

---

## Market Sentiment

### US — 5-Tier (Trend Setter Breadth)

Determined by the percentage of **Trend Setter** stocks trading below their 60-day MA. Returned by `GET /scan/last` as `market_sentiment.status` and `market_sentiment.below_60ma_pct`. Contextual backdrop only — does NOT gate signal logic.

| % Below 60MA | Sentiment | Icon | Guidance |
|--------------|-----------|------|----------|
| 0–10% | `STRONG_BULLISH` | ☀️ | Nearly all trend setters healthy — strong breadth, full risk-on |
| 10–30% | `BULLISH` | 🌤️ | Mostly healthy — normal accumulation conditions |
| 30–50% | `NEUTRAL` | ⛅ | Mixed breadth — transition zone, be selective |
| 50–70% | `BEARISH` | 🌧️ | Majority weakening — reduce exposure, tighten stops |
| >70% | `STRONG_BEARISH` | ⛈️ | Extreme weakness — defensive posture, cash is king |

### JP — Nikkei Volatility Index (`^JNV`)

Returned as `"JP"` key when user holds `.T` (Japan) tickers alongside the standard `"US"` Fear & Greed composite.

| Nikkei VI | Level | Guidance |
|-----------|-------|----------|
| ≥ 35 | Extreme Fear | JP market panic — contrarian opportunity zone |
| 25–35 | Fear | JP market cautious — selective accumulation |
| 18–25 | Neutral | JP market balanced — normal positioning |
| 14–18 | Greed | JP market confident — watch for overheating |
| < 14 | Extreme Greed | JP market euphoric — reduce exposure |

### TW — TAIEX Realized Volatility (`^TWII`)

Returned as `"TW"` key when user holds `.TW` (Taiwan) tickers. `source` = `"TAIEX Realized Vol"`. Computed as `std(log_returns) × √252 × 100` (20-day annualized). Key is absent when no `.TW` tickers tracked.

| Realized Vol | Level | Guidance |
|-------------|-------|----------|
| > 30% | Extreme Fear | TW market panic — contrarian opportunity zone |
| 22–30% | Fear | TW market cautious — selective accumulation |
| 15–22% | Neutral | TW market balanced — normal positioning |
| 10–15% | Greed | TW market confident — watch for overheating |
| < 10% | Extreme Greed | TW market euphoric — reduce exposure |

---

## Daily Change Tracking

### `GET /ticker/{ticker}/signals` — Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `price` | float | Current close price |
| `previous_close` | float? | Previous trading day close |
| `change_pct` | float? | Daily change % (e.g., `2.50` = +2.50%) |
| `rsi` | float | RSI(14) |
| `ma200` | float | 200-day moving average |
| `ma60` | float | 60-day moving average |
| `bias` | float | Price deviation from 60MA (%) |
| `volume_ratio` | float | Recent/average volume ratio |
| `status` | list[str] | Formatted status descriptions |
| `bias_percentile` | float? | Current bias rank in 3-year historical distribution (0–100); `97.0` = top 3% historically |
| `is_rogue_wave` | bool | `true` when `bias_percentile ≥ 95` AND `volume_ratio ≥ 1.5` |

### `GET /rebalance` — Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_value` | float | Current portfolio total market value |
| `previous_total_value` | float? | Previous trading day portfolio total |
| `total_value_change` | float? | Daily change amount |
| `total_value_change_pct` | float? | Daily change percentage |
| `holdings_detail[].change_pct` | float? | Per-holding daily change % |
| `holdings_detail[].cost_total` | float? | Total cost basis |
| `holdings_detail[].purchase_fx_rate` | float? | FX rate at purchase time (1 unit holding currency = ? USD) |
| `holdings_detail[].current_fx_rate` | float? | Current FX rate; compute FX return: `(current / purchase − 1) × 100` |
| `xray` | array | True exposure per stock (direct + indirect via ETFs) |

**Edge cases:**
- `previous_close` / `change_pct` are `null` for stocks with < 2 days of history
- Weekend/holiday gaps handled automatically by yfinance (uses last trading day)
- Cash holdings: no price change (same current and previous value)

---

## Full Direct API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/summary` | Plain-text portfolio summary (total value + daily change + signals + movers + drift + Smart Money) |
| `GET` | `/stocks` | All tracked stocks (includes `last_scan_signal`) |
| `GET` | `/stocks/export` | Export watchlist (JSON) |
| `POST` | `/ticker` | Add stock |
| `GET` | `/ticker/{ticker}/signals` | Technical signals (RSI, MA, Bias, rogue wave) |
| `GET` | `/ticker/{ticker}/moat` | Moat analysis (gross margin YoY) |
| `POST` | `/ticker/{ticker}/thesis` | Update investment thesis |
| `PATCH` | `/ticker/{ticker}/category` | Switch category |
| `GET` | `/ticker/{ticker}/scan-history` | Scan history |
| `GET` | `/ticker/{ticker}/alerts` | Price alert list |
| `POST` | `/ticker/{ticker}/alerts` | Create price alert |
| `PATCH` | `/alerts/{alert_id}/toggle` | Toggle alert active ↔ paused |
| `DELETE` | `/alerts/{alert_id}` | Delete alert |
| `GET` | `/ticker/{ticker}/earnings` | Earnings calendar |
| `GET` | `/ticker/{ticker}/dividend` | Dividend info |
| `POST` | `/scan` | Trigger full portfolio scan |
| `GET` | `/scan/last` | Last scan timestamp + market sentiment + F&G |
| `POST` | `/digest` | Trigger weekly digest |
| `GET` | `/snapshots` | Historical snapshots — `?days=30` (1–730) or `?start=YYYY-MM-DD&end=YYYY-MM-DD` |
| `GET` | `/snapshots/twr` | Time-weighted return — `?start=&end=` (defaults YTD); `twr_pct` null when < 2 snapshots |
| `POST` | `/snapshots/take` | Trigger today's snapshot (background, upsert) |
| `GET` | `/personas/templates` | Investment persona templates |
| `GET` | `/profiles` | Active investment profile |
| `POST` | `/profiles` | Create investment profile |
| `GET` | `/holdings` | All holdings |
| `POST` | `/holdings` | Add holding (body: `ticker`, `quantity`, `cost`, `currency`; auto-snapshots FX rate) |
| `POST` | `/holdings/cash` | Add cash holding |
| `GET` | `/rebalance` | Rebalance + X-Ray; add `?display_currency=TWD` |
| `POST` | `/rebalance/xray-alert` | Telegram alert for stocks with true exposure > 15% |
| `GET` | `/stress-test` | Stress test (`?scenario_drop_pct=-20&display_currency=USD`); returns Beta, expected loss, pain level |
| `GET` | `/currency-exposure` | Currency exposure: `breakdown`, `cash_breakdown`, `fx_rate_alerts` (three-tier), FX movements |
| `POST` | `/currency-exposure/alert` | Telegram alert for three-tier FX rate changes (daily >1.5%, 5-day >2%, 3-month >8%) |
| `GET` | `/fx-watch` | FX watch configs (`?active_only=true`) |
| `POST` | `/fx-watch` | Create FX watch: `base_currency`, `quote_currency`, `recent_high_days`, `consecutive_increase_days`, `alert_on_recent_high`, `alert_on_consecutive_increase`, `reminder_interval_hours` |
| `PATCH` | `/fx-watch/{watch_id}` | Partial update (any field incl. `is_active`) |
| `DELETE` | `/fx-watch/{watch_id}` | Delete FX watch |
| `POST` | `/fx-watch/check` | Analyze all active watches (no Telegram); returns rate, near-high status, consecutive days |
| `POST` | `/fx-watch/alert` | Analyze + send Telegram (per-watch cooldown); returns `total_watches`, `triggered_alerts`, `sent_alerts` |
| `POST` | `/withdraw` | Smart withdrawal — body: `{"target_amount": 50000, "display_currency": "TWD", "notify": true}` |
| `GET` | `/market/fear-greed` | Fear & Greed Index (VIX + CNN composite) |
| `GET` | `/settings/telegram` | Telegram settings (token masked) |
| `PUT` | `/settings/telegram` | Update Telegram settings (dual-mode) |
| `POST` | `/settings/telegram/test` | Send test Telegram message |
| `GET` | `/settings/preferences` | Language + privacy preferences |
| `PUT` | `/settings/preferences` | Update preferences — `language`: `zh-TW`/`en`/`ja`/`zh-CN` |
| `GET` | `/gurus` | All tracked gurus (id, name, display_name, cik, active) |
| `POST` | `/gurus` | Add guru — body: `{"name": "Berkshire Hathaway Inc", "cik": "0001067983", "display_name": "Warren Buffett"}` |
| `DELETE` | `/gurus/{guru_id}` | Deactivate guru (history preserved) |
| `POST` | `/gurus/sync` | Batch-sync all guru 13F from SEC EDGAR (mutex-protected) |
| `POST` | `/gurus/{guru_id}/sync` | Sync one guru — returns `{"status": "synced"\|"skipped", "message": "..."}` |
| `GET` | `/gurus/{guru_id}/filing` | Latest 13F summary: report_date, filing_date, total_value, holdings_count, new/sold/increased/decreased |
| `GET` | `/gurus/{guru_id}/filings` | All historical 13F filing records |
| `GET` | `/gurus/{guru_id}/holdings` | All holdings with action labels (NEW_POSITION/SOLD_OUT/INCREASED/DECREASED/UNCHANGED); add `?include_performance=true` for `price_change_pct` since filing |
| `GET` | `/gurus/{guru_id}/top` | Top N holdings by weight — `?n=10`; add `?include_performance=true` |
| `GET` | `/gurus/{guru_id}/qoq` | Quarter-over-quarter history — `?quarters=N` (default 3); `trend`: increasing/decreasing/new/exited/stable |
| `GET` | `/gurus/grand-portfolio` | Cross-guru aggregated view: `items` (ticker, combined_weight_pct, dominant_action, sector, guru_count), `sector_breakdown` |
| `GET` | `/resonance` | Guru × watchlist/holdings overlap: `{results: [{guru_display_name, overlapping_tickers, overlap_count, holdings}], total_gurus, gurus_with_overlap}` |
| `GET` | `/resonance/{ticker}` | Which gurus hold a specific ticker and their current action |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI spec |

---

## Service Operations

Run all `make` commands from the Folio project root using the `exec` tool.

### Backup & Restore

| Command | Description |
|---------|-------------|
| `make backup` | Backup database to `./backups/radar-YYYYMMDD_HHMMSS.db` |
| `make restore` | Restore from the latest backup in `./backups/` |
| `make restore FILE=backups/radar-20260214.db` | Restore from a specific backup file |

### Upgrade & Restart

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `git pull origin main` | Fetch latest code |
| 2 | `make up` | Rebuild images and restart (zero downtime, data preserved) |
| 3 | `curl -sf http://localhost:8000/health` | Verify backend health |
| 4 | `docker compose ps` | Confirm all containers running |
| 5 | `docker compose logs backend --tail 50` | Troubleshoot if health check fails |

> `docker compose down -v` — full reset, **DELETES ALL DATA**. Always `make backup` first.

### Health & Diagnostics

| Command | Description |
|---------|-------------|
| `curl -sf http://localhost:8000/health` | Backend health check |
| `docker compose ps` | Container status |
| `docker compose logs backend --tail 50` | Recent backend logs |

---

## Guru 13F Filing Schedule

During 13F filing seasons (February, May, August, November), the cron service automatically calls `POST /gurus/sync` daily. Off-season it runs weekly. Use `POST /gurus/{id}/sync` manually to force a refresh; `"skipped"` means the data is already current.
