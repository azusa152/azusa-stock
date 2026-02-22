export interface Guru {
  id: number
  name: string
  cik: string
  display_name: string
  is_active: boolean
  is_default: boolean
}

export interface GuruSummaryItem {
  id: number
  display_name: string
  latest_report_date: string | null
  latest_filing_date: string | null
  total_value: number | null
  holdings_count: number
  filing_count: number
}

export interface SeasonHighlightItem {
  ticker: string | null
  company_name: string
  guru_id: number
  guru_display_name: string
  value: number
  weight_pct: number | null
  change_pct: number | null
}

export interface SeasonHighlights {
  new_positions: SeasonHighlightItem[]
  sold_outs: SeasonHighlightItem[]
}

export interface ConsensusStockItem {
  ticker: string
  guru_count: number
  gurus: string[]
  total_value: number
}

export interface SectorBreakdownItem {
  sector: string
  total_value: number
  holding_count: number
  weight_pct: number
}

export interface DashboardResponse {
  gurus: GuruSummaryItem[]
  season_highlights: SeasonHighlights
  consensus: ConsensusStockItem[]
  sector_breakdown: SectorBreakdownItem[]
}

export interface GuruFiling {
  guru_id: number
  guru_display_name: string
  report_date: string | null
  filing_date: string | null
  total_value: number | null
  holdings_count: number
  filing_url: string
  new_positions: number
  sold_out: number
  increased: number
  decreased: number
  top_holdings: Record<string, unknown>[]
}

export interface GuruHolding {
  guru_id: number
  cusip: string
  ticker: string | null
  company_name: string
  value: number
  shares: number
  action: string
  change_pct: number | null
  weight_pct: number | null
  report_date: string | null
  filing_date: string | null
}

export interface FilingHistoryItem {
  id: number
  report_date: string
  filing_date: string
  total_value: number | null
  holdings_count: number
  filing_url: string
}

export interface FilingHistoryResponse {
  filings: FilingHistoryItem[]
}

// guru with action detail (for great-minds gurus field)
export interface GreatMindsGuruDetail {
  guru_id: number
  guru_display_name: string
  action: string
  weight_pct: number | null
}

export interface GreatMindsEntryResponse {
  ticker: string
  guru_count: number
  gurus: GreatMindsGuruDetail[]
}

export interface GreatMindsResponse {
  stocks: GreatMindsEntryResponse[]
  total_count: number
}

export interface AddGuruRequest {
  name: string
  cik: string
  display_name: string
}
