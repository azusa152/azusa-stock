import type { components } from "./generated"

// ---------------------------------------------------------------------------
// Generated from backend Pydantic schemas (single source of truth)
// Do NOT manually edit types that correspond to backend response_model schemas.
// Run `make generate-api` after changing backend/api/schemas.py.
// ---------------------------------------------------------------------------

export type Guru = components["schemas"]["GuruResponse"]
export type GuruSummaryItem = components["schemas"]["GuruSummaryItem"]
export type SeasonHighlightItem = components["schemas"]["SeasonHighlightItem"]
export type SeasonHighlights = components["schemas"]["SeasonHighlights"]
export type ConsensusGuruDetail = components["schemas"]["ConsensusGuruDetail"]
export type ConsensusStockItem = components["schemas"]["ConsensusStockItem"]
export type SectorBreakdownItem = components["schemas"]["SectorBreakdownItem"]
export type ActivityFeedItem = components["schemas"]["ActivityFeedItem"]
export type ActivityFeed = components["schemas"]["ActivityFeed"]
export type DashboardResponse = components["schemas"]["DashboardResponse"]

export type GuruFiling = components["schemas"]["GuruFilingResponse"]
export type GuruHolding = components["schemas"]["GuruHoldingResponse"]
export type FilingHistoryItem = components["schemas"]["FilingHistoryItem"]
export type FilingHistoryResponse = components["schemas"]["FilingHistoryResponse"]
export type QoQQuarterSnapshot = components["schemas"]["QoQQuarterSnapshot"]
export type QoQHoldingItem = components["schemas"]["QoQHoldingItem"]
export type QoQResponse = components["schemas"]["QoQResponse"]

// GreatMindsEntryResponse.gurus is list[dict] in the backend → typed as unknown[] in the generated type.
// Provide a properly typed override for frontend rendering.
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

// Request types
export type AddGuruRequest = components["schemas"]["GuruCreate"]
