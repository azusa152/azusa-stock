export const CATEGORY_ICON_SHORT: Record<string, string> = {
  Trend_Setter: "🌊",
  Moat: "🏰",
  Growth: "🚀",
  Bond: "🛡️",
  Cash: "💵",
}

export const CATEGORY_COLOR_MAP: Record<string, string> = {
  Trend_Setter: "#3B82F6",
  Moat: "#10B981",
  Growth: "#F59E0B",
  Bond: "#8B5CF6",
  Cash: "#9CA3AF",
}

export const CATEGORY_COLOR_FALLBACK = "#CBD5E1"

export const SCAN_SIGNAL_ICONS: Record<string, string> = {
  THESIS_BROKEN: "🚨",
  DEEP_VALUE: "💎",
  OVERSOLD: "📉",
  CONTRARIAN_BUY: "🟢",
  APPROACHING_BUY: "🎯",
  OVERHEATED: "🔥",
  CAUTION_HIGH: "⚠️",
  WEAKENING: "🔻",
  NORMAL: "➖",
}

export const BUY_OPPORTUNITY_SIGNALS = new Set([
  "DEEP_VALUE",
  "OVERSOLD",
  "CONTRARIAN_BUY",
  "APPROACHING_BUY",
])

export const RISK_WARNING_SIGNALS = new Set([
  "THESIS_BROKEN",
  "OVERHEATED",
  "CAUTION_HIGH",
])

export const STOCK_CATEGORIES = [
  "Trend_Setter",
  "Moat",
  "Growth",
  "Bond",
  "Cash",
] as const

export const RADAR_CATEGORIES = [
  "Trend_Setter",
  "Moat",
  "Growth",
  "Bond",
] as const

export const MARKET_TAG_OPTIONS: Record<string, string[]> = {
  US: ["AI", "Cloud", "SaaS", "Semi", "Infra", "Pharma", "Energy", "Finance"],
  JP: ["Auto", "Electronics", "Trading", "Pharma", "Finance", "REIT", "Semi", "Robotics"],
  TW: ["Semi", "TSMC Supply", "Finance", "Telecom", "Biotech", "ETF"],
  HK: ["Tech", "Finance", "Property", "Telecom", "Energy", "Consumer"],
}

// Keep for backward compatibility
export const DEFAULT_TAG_OPTIONS = MARKET_TAG_OPTIONS.US

export const CASH_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "HKD"]

export const DISPLAY_CURRENCIES = ["USD", "TWD", "JPY", "HKD", "EUR", "GBP"]

export const FX_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "EUR", "GBP", "CNY", "HKD", "SGD", "THB"]

export const ACCOUNT_TYPES = ["savings", "time_deposit", "money_market", "other"] as const

/** Shared chart color palette for pie/bar/treemap charts without category semantics. */
export const CHART_COLOR_PALETTE = [
  "#3b82f6", "#22c55e", "#f97316", "#a855f7", "#06b6d4", "#ec4899", "#eab308",
] as const

export const MARKET_HOURS: Record<string, { tz: string; open: string; close: string; lunch?: [string, string] }> = {
  US: { tz: "America/New_York", open: "09:30", close: "16:00" },
  JP: { tz: "Asia/Tokyo", open: "09:00", close: "15:30", lunch: ["11:30", "12:30"] },
  TW: { tz: "Asia/Taipei", open: "09:00", close: "13:30" },
  HK: { tz: "Asia/Hong_Kong", open: "09:30", close: "16:00", lunch: ["12:00", "13:00"] },
}

// Market options: labelKey references config.market.* i18n keys
export const MARKET_OPTIONS = [
  { key: "US", labelKey: "config.market.us", suffix: "", currency: "USD" },
  { key: "TW", labelKey: "config.market.tw", suffix: ".TW", currency: "TWD" },
  { key: "JP", labelKey: "config.market.jp", suffix: ".T", currency: "JPY" },
  { key: "HK", labelKey: "config.market.hk", suffix: ".HK", currency: "HKD" },
] as const
