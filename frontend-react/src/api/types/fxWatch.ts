export interface FxWatch {
  id: number
  base_currency: string
  quote_currency: string
  recent_high_days: number
  consecutive_increase_days: number
  alert_on_recent_high: boolean
  alert_on_consecutive_increase: boolean
  reminder_interval_hours: number
  is_active: boolean
  last_alerted_at: string | null
}

export interface FxAnalysis {
  current_rate: number
  should_alert: boolean
  recommendation: string
  reasoning: string
}

export interface FxHistoryPoint {
  date: string
  close: number
}

// POST /fx-watch/check returns map of watch_id → analysis
export type FxAnalysisMap = Record<number, FxAnalysis>

// Raw response shape from POST /fx-watch/check
export interface FxCheckResponse {
  total_watches: number
  results: Array<{
    watch_id: number
    pair: string
    result: {
      current_rate: number
      should_alert: boolean
      recommendation_zh: string
      reasoning_zh: string
    }
  }>
}

export interface CreateFxWatchRequest {
  base_currency: string
  quote_currency: string
  recent_high_days: number
  consecutive_increase_days: number
  alert_on_recent_high: boolean
  alert_on_consecutive_increase: boolean
  reminder_interval_hours: number
}

export interface UpdateFxWatchRequest {
  recent_high_days?: number
  consecutive_increase_days?: number
  alert_on_recent_high?: boolean
  alert_on_consecutive_increase?: boolean
  reminder_interval_hours?: number
  is_active?: boolean
}
