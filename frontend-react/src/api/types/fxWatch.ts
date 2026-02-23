import type { components } from "./generated"

// ---------------------------------------------------------------------------
// Generated from backend Pydantic schemas (single source of truth)
// Do NOT manually edit types that correspond to backend response_model schemas.
// Run `make generate-api` after changing backend/api/schemas.py.
// ---------------------------------------------------------------------------

// FxWatch config item (mapped from FXWatchResponse)
export type FxWatch = components["schemas"]["FXWatchResponse"]

// POST /fx-watch/check full response
export type FxCheckResponse = components["schemas"]["FXWatchCheckResponse"]

// Request types
export type CreateFxWatchRequest = components["schemas"]["FXWatchCreateRequest"]
export type UpdateFxWatchRequest = components["schemas"]["FXWatchUpdateRequest"]

// ---------------------------------------------------------------------------
// Hand-written types: derived/transformed shapes used in the frontend
// ---------------------------------------------------------------------------

// FXTimingResultResponse nested inside FXWatchCheckResultItem.
// Kept hand-written because useFxWatch maps it into a flattened, frontend-facing shape
// and renames two fields: recommendation_zh → recommendation, reasoning_zh → reasoning,
// dropping the language suffix so components stay language-agnostic.
export interface FxAnalysis {
  current_rate: number
  should_alert: boolean
  recommendation: string
  reasoning: string
  is_recent_high: boolean
  lookback_high: number
  lookback_days: number
  consecutive_increases: number
  consecutive_threshold: number
}

// GET /forex/{base}/{quote}/history-long returns list[dict]
export interface FxHistoryPoint {
  date: string
  close: number
}

// Inverted map used by FX watch components: watch_id → analysis
export type FxAnalysisMap = Record<number, FxAnalysis>
