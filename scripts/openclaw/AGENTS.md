# Azusa Radar — OpenClaw Workspace Instructions

## System Context

You have access to **Azusa Radar (投資雷達)**, a self-hosted stock tracking and market scanning system. It runs as a Docker Compose application with a FastAPI backend at `http://localhost:8000`.

## How to Interact

Use the `exec` tool with `curl` to call the Azusa Radar API:

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
| `summary` | Portfolio health + stock list |
| `signals` | Technical indicators for a ticker (RSI, MA, Bias) |
| `scan` | Trigger background full scan (results via Telegram) |
| `moat` | Gross margin YoY analysis for a ticker |
| `alerts` | List price alerts for a ticker |
| `add_stock` | Add stock with `params: {ticker, category, thesis, tags}` |

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

### Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Response Guidelines

- Be concise — the user wants quick investment insights, not essays
- When asked about portfolio status, call `/summary` first
- When asked about a specific stock, call `/webhook` with `signals` or `moat`
- Present data in a structured, readable format
- Use the stock categories to contextualize advice:
  - **Trend_Setter (風向球)**: Market direction indicators
  - **Moat (護城河)**: Companies with competitive advantages
  - **Growth (成長夢想)**: High-volatility growth stocks
  - **ETF**: Index funds for passive tracking
