import type { StockCategory, ScanSignal } from "./dashboard"

export type { StockCategory, ScanSignal }

export interface RadarStock {
  id: number
  ticker: string
  category: StockCategory
  is_active: boolean
  is_etf: boolean
  current_thesis: string
  current_tags: string[]
  last_scan_signal: ScanSignal
  display_order: number
  created_at?: string
  updated_at?: string
}

export interface RemovedStock {
  ticker: string
  category: StockCategory
  current_thesis: string
  removal_reason: string
  removed_at?: string
}

export interface ScanStatusResponse {
  is_running: boolean
}

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

// Resonance: GET /resonance returns guru-centric list
export interface ResonanceEntry {
  guru_id: number
  guru_display_name: string
  overlapping_tickers: string[]
  overlap_count: number
  holdings: ResonanceHolding[]
}

export interface ResonanceHolding {
  ticker: string
  action: string
  weight_pct?: number
}

export interface ResonanceResponse {
  results: ResonanceEntry[]
  total_gurus: number
  gurus_with_overlap: number
}

// Inverted map: ticker → list of gurus holding it (used for stock cards)
export type ResonanceMap = Record<string, (ResonanceHolding & { guru_display_name: string })[]>

// Enriched stock signals (from /stocks/enriched)
export interface RadarSignals {
  price?: number
  change_pct?: number
  rsi?: number
  ma200?: number
  ma60?: number
  bias?: number
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

// Add stock request
export interface AddStockRequest {
  ticker: string
  category: StockCategory
  thesis: string
  tags: string[]
  is_etf?: boolean
}

// Deactivate request
export interface DeactivateRequest {
  reason: string
}

// Reactivate request
export interface ReactivateRequest {
  category: StockCategory
  thesis?: string
}

// Category update request
export interface UpdateCategoryRequest {
  category: StockCategory
}

// Reorder request
export interface ReorderRequest {
  ordered_tickers: string[]
}

// Thesis add request
export interface AddThesisRequest {
  content: string
  tags?: string[]
}

// Import item
export interface StockImportItem {
  ticker: string
  category: StockCategory
  thesis: string
  tags?: string[]
  is_etf?: boolean
}
