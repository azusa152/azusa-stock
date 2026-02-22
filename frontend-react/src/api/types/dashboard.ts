export type StockCategory =
  | "Trend_Setter"
  | "Moat"
  | "Growth"
  | "Bond"
  | "Cash"

export type ScanSignal =
  | "NORMAL"
  | "DEEP_VALUE"
  | "OVERSOLD"
  | "CONTRARIAN_BUY"
  | "OVERHEATED"
  | "CAUTION_HIGH"
  | "WEAKENING"
  | "THESIS_BROKEN"

export interface Stock {
  ticker: string
  category: StockCategory
  current_thesis: string
  current_tags: string[]
  display_order: number
  last_scan_signal: ScanSignal
  is_active: boolean
  is_etf: boolean
  signals?: Record<string, unknown>
}

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

export interface CategoryAllocation {
  target_pct: number
  current_pct: number
  drift_pct: number
  current_value: number
}

export interface HoldingDetail {
  ticker: string
  category: StockCategory
  quantity: number
  cost_basis?: number
  cost_total?: number
  market_value: number
  weight_pct: number
  change_pct?: number
  fx?: number
  currency?: string
}

export interface RebalanceResponse {
  total_value: number
  previous_total_value?: number
  total_value_change?: number
  total_value_change_pct?: number
  display_currency: string
  categories: Record<string, CategoryAllocation>
  advice: string[]
  holdings_detail: HoldingDetail[]
  health_score: number
  health_level: string
  calculated_at: string
}

export interface VIXData {
  value?: number
  change_1d?: number
}

export interface CNNFearGreedData {
  score?: number
  rating?: string
}

export interface FearGreedResponse {
  composite_score: number
  composite_level: string
  composite_label: string
  vix?: VIXData
  cnn?: CNNFearGreedData
  fetched_at: string
}

export interface Snapshot {
  snapshot_date: string
  total_value: number
  category_values?: Record<string, number>
  display_currency?: string
  benchmark_value?: number
}

export interface TwrResponse {
  twr_pct?: number
  start_date?: string
  end_date?: string
  snapshot_count: number
}

export interface GreatMindsGuru {
  guru_id: string
  guru_display_name: string
  action: string
  weight_pct?: number
}

export interface GreatMindsEntry {
  ticker: string
  guru_count: number
  gurus: GreatMindsGuru[]
}

export interface GreatMindsResponse {
  stocks: GreatMindsEntry[]
  total_count: number
}

export interface LastScanResponse {
  last_scanned_at?: string
  epoch?: number
  market_status?: string
  market_status_details?: string
  fear_greed_level?: string
  fear_greed_score?: number
}

export interface Holding {
  id: number
  ticker: string
  category: StockCategory
  quantity: number
  cost_basis?: number
  broker?: string
  currency: string
  account_type?: string
  is_cash: boolean
  updated_at: string
}

export interface ProfileResponse {
  id: number
  user_id: string
  name: string
  source_template_id?: string
  home_currency: string
  config: Record<string, number>
  is_active: boolean
  created_at: string
  updated_at: string
}
