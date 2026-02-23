import type { components } from "./generated"

// ---------------------------------------------------------------------------
// Generated from backend Pydantic schemas (single source of truth)
// Do NOT manually edit types that correspond to backend response_model schemas.
// Run `make generate-api` after changing backend/api/schemas.py.
// ---------------------------------------------------------------------------

export type StockCategory = components["schemas"]["StockCategory"]
export type ScanSignal = components["schemas"]["ScanSignal"]

// Stock list item (mapped from StockResponse)
export type RadarStock = components["schemas"]["StockResponse"]

export type RemovedStock = components["schemas"]["RemovedStockResponse"]
export type ScanStatusResponse = components["schemas"]["ScanStatusResponse"]
export type ResonanceResponse = components["schemas"]["ResonanceResponse"]

// Request types
export type AddStockRequest = components["schemas"]["TickerCreateRequest"]
export type DeactivateRequest = components["schemas"]["DeactivateRequest"]
export type ReactivateRequest = components["schemas"]["ReactivateRequest"]
export type UpdateCategoryRequest = components["schemas"]["CategoryUpdateRequest"]
export type ReorderRequest = components["schemas"]["ReorderRequest"]
export type AddThesisRequest = components["schemas"]["ThesisCreateRequest"]
export type StockImportItem = components["schemas"]["StockImportItem"]

// ---------------------------------------------------------------------------
// Hand-written types: backend endpoints return untyped dict for these
// ---------------------------------------------------------------------------

// GET /stocks/enriched returns list[dict] — no Pydantic response_model
export interface RadarSignals {
  price?: number
  previous_close?: number
  change_pct?: number
  rsi?: number
  ma200?: number
  ma60?: number
  bias?: number
  bias_200?: number
  volume_ratio?: number
  institutional_holders?: Record<string, unknown>[]
}

export interface RadarEnrichedStock {
  ticker: string
  category?: StockCategory
  last_scan_signal?: ScanSignal
  computed_signal?: ScanSignal
  price?: number
  change_pct?: number
  rsi?: number
  bias?: number
  volume_ratio?: number
  signals?: RadarSignals
  dividend?: {
    dividend_yield?: number
    ex_date?: string
    error?: string
  }
  earnings?: {
    next_earnings_date?: string
    days_until?: number
    error?: string
  }
}

// GET /ticker/{ticker}/thesis and /ticker/{ticker}/removals return list[dict]
export interface ThesisLog {
  version: number
  content: string
  tags: string[]
  created_at: string
}

export interface RemovalLog {
  reason: string
  created_at: string
}

// GET /resonance returns guru-centric structure; backend ResonanceResponse
// contains nested dicts — typed here for frontend rendering
export interface ResonanceHolding {
  ticker: string
  action: string
  weight_pct?: number
}

export interface ResonanceEntry {
  guru_id: number
  guru_display_name: string
  overlapping_tickers: string[]
  overlap_count: number
  holdings: ResonanceHolding[]
}

// Inverted map: ticker → list of gurus holding it (used for stock cards)
export type ResonanceMap = Record<string, (ResonanceHolding & { guru_display_name: string })[]>
