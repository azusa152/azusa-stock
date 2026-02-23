import type { components } from "./generated"

// ---------------------------------------------------------------------------
// Generated from backend Pydantic schemas (single source of truth)
// Do NOT manually edit types that correspond to backend response_model schemas.
// Run `make generate-api` after changing backend/api/schemas.py.
// ---------------------------------------------------------------------------

export type StockCategory = components["schemas"]["StockCategory"]
export type ScanSignal = components["schemas"]["ScanSignal"]

// Stock (mapped from StockResponse)
export type Stock = components["schemas"]["StockResponse"]

export type CategoryAllocation = components["schemas"]["CategoryAllocation"]
export type HoldingDetail = components["schemas"]["HoldingDetail"]
export type RebalanceResponse = components["schemas"]["RebalanceResponse"]

export type VIXData = components["schemas"]["VIXData"]
export type CNNFearGreedData = components["schemas"]["CNNFearGreedData"]
export type FearGreedResponse = components["schemas"]["FearGreedResponse"]

// Snapshot (mapped from SnapshotResponse)
export type Snapshot = components["schemas"]["SnapshotResponse"]
export type TwrResponse = components["schemas"]["TwrResponse"]

// GreatMindsResponse: gurus field is list[dict] in backend → properly typed via hand-written types
export type { GreatMindsResponse, GreatMindsEntryResponse, GreatMindsGuruDetail } from "./smartMoney"
export type LastScanResponse = components["schemas"]["LastScanResponse"]

// Holding (mapped from HoldingResponse)
export type Holding = components["schemas"]["HoldingResponse"]

export type ProfileResponse = components["schemas"]["ProfileResponse"]

// ---------------------------------------------------------------------------
// Hand-written types: backend endpoints return untyped dict for these
// ---------------------------------------------------------------------------

export interface DividendInfo {
  dividend_yield?: number
  ex_date?: string
  ytd_dividend_per_share?: number
  error?: string
}

export interface EarningsInfo {
  next_earnings_date?: string
  days_until?: number
  error?: string
}

// GET /stocks/enriched returns list[dict] — no Pydantic response_model
export interface EnrichedStock {
  ticker: string
  category?: StockCategory
  last_scan_signal?: ScanSignal
  computed_signal?: ScanSignal
  price?: number
  change_pct?: number
  rsi?: number
  bias?: number
  dividend?: DividendInfo
  earnings?: EarningsInfo
}

