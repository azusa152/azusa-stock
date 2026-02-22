// Types that already exist in dashboard.ts are imported from there to avoid duplication
export type { StockCategory, CategoryAllocation, HoldingDetail, Holding, ProfileResponse } from "./dashboard"

// ---------------------------------------------------------------------------
// Persona templates
// ---------------------------------------------------------------------------

export interface PersonaTemplate {
  id: string
  name: string
  description: string
  quote: string
  is_empty: boolean
  default_config: Record<string, number>
}

// ---------------------------------------------------------------------------
// Extended rebalance types (fields not in dashboard.ts RebalanceResponse)
// ---------------------------------------------------------------------------

export interface XRayEntry {
  symbol: string
  name: string
  direct_value: number
  direct_weight_pct: number
  indirect_value: number
  indirect_weight_pct: number
  total_value: number
  total_weight_pct: number
  indirect_sources: string[]
}

export interface SectorExposureItem {
  sector: string
  value: number
  weight_pct: number
  equity_pct: number
}

export interface AllocRebalanceResponse {
  total_value: number
  previous_total_value?: number
  total_value_change?: number
  total_value_change_pct?: number
  display_currency: string
  categories: Record<string, import("./dashboard").CategoryAllocation>
  advice: string[]
  holdings_detail: import("./dashboard").HoldingDetail[]
  xray: XRayEntry[]
  health_score: number
  health_level: string
  sector_exposure: SectorExposureItem[]
  calculated_at: string
}

// ---------------------------------------------------------------------------
// Currency exposure
// ---------------------------------------------------------------------------

export interface CurrencyBreakdown {
  currency: string
  value: number
  percentage: number
  is_home: boolean
}

export interface FXMovement {
  pair: string
  current_rate: number
  change_pct: number
  direction: string
}

export interface FXRateAlertItem {
  pair: string
  alert_type: string
  change_pct: number
  direction: string
  current_rate: number
  period_label: string
}

export interface CurrencyExposureResponse {
  home_currency: string
  total_value_home: number
  breakdown: CurrencyBreakdown[]
  non_home_pct: number
  cash_breakdown: CurrencyBreakdown[]
  cash_non_home_pct: number
  total_cash_home: number
  fx_movements: FXMovement[]
  fx_rate_alerts: FXRateAlertItem[]
  risk_level: string
  advice: string[]
  calculated_at: string
}

// ---------------------------------------------------------------------------
// Stress test
// ---------------------------------------------------------------------------

export interface StressTestHoldingBreakdown {
  ticker: string
  category: string
  beta: number
  market_value: number
  expected_drop_pct: number
  expected_loss: number
}

export interface StressTestPainLevel {
  level: string
  label: string
  emoji: string
}

export interface StressTestResponse {
  portfolio_beta: number
  scenario_drop_pct: number
  total_value: number
  total_loss: number
  total_loss_pct: number
  display_currency: string
  pain_level: StressTestPainLevel
  advice: string[]
  disclaimer: string
  holdings_breakdown: StressTestHoldingBreakdown[]
}

// ---------------------------------------------------------------------------
// Smart withdrawal
// ---------------------------------------------------------------------------

export interface SellRecommendation {
  ticker: string
  category: string
  quantity_to_sell: number
  sell_value: number
  reason: string
  unrealized_pl: number
  priority: number
}

export interface PostSellDrift {
  target_pct: number
  current_pct: number
  drift_pct: number
  market_value: number
}

export interface WithdrawResponse {
  recommendations: SellRecommendation[]
  total_sell_value: number
  target_amount: number
  shortfall: number
  post_sell_drifts: Record<string, PostSellDrift>
  message: string
}

// ---------------------------------------------------------------------------
// Telegram & Notification Preferences
// ---------------------------------------------------------------------------

export interface TelegramSettings {
  telegram_chat_id: string
  custom_bot_token_masked: string
  use_custom_bot: boolean
}

export interface AllocPreferencesResponse {
  language: string
  privacy_mode: boolean
  notification_preferences: Record<string, boolean>
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface AddHoldingRequest {
  ticker: string
  category: string
  quantity: number
  cost_basis?: number
  broker?: string
  currency: string
  market?: string
}

export interface AddCashRequest {
  currency: string
  amount: number
  bank?: string
  account_type?: string
  notes?: string
}

export interface UpdateHoldingRequest {
  quantity?: number
  cost_basis?: number
  broker?: string
  category?: string
}

export interface WithdrawRequest {
  amount: number
  currency: string
  notify: boolean
}

export interface CreateProfileRequest {
  name: string
  home_currency: string
  source_template_id?: string
  config: Record<string, number>
}

export interface UpdateProfileRequest {
  name?: string
  home_currency?: string
  config?: Record<string, number>
}

export interface SaveTelegramRequest {
  telegram_chat_id: string
  custom_bot_token?: string
  use_custom_bot: boolean
}

export interface SavePreferencesRequest {
  notification_preferences: Record<string, boolean>
}
