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
  THESIS_BROKEN: "🔴",
  DEEP_VALUE: "💎",
  OVERSOLD: "📉",
  CONTRARIAN_BUY: "🟢",
  OVERHEATED: "🔥",
  CAUTION_HIGH: "⚠️",
  WEAKENING: "📊",
  NORMAL: "⚪",
}

export const BUY_OPPORTUNITY_SIGNALS = new Set([
  "DEEP_VALUE",
  "OVERSOLD",
  "CONTRARIAN_BUY",
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

export const DEFAULT_TAG_OPTIONS = [
  "AI",
  "Cloud",
  "SaaS",
  "Semi",
  "Infra",
  "Pharma",
  "Energy",
  "Finance",
]

export const CASH_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "HKD"]

// Market options: labelKey references config.market.* i18n keys
export const MARKET_OPTIONS = [
  { key: "US", labelKey: "config.market.us", suffix: "", currency: "USD" },
  { key: "TW", labelKey: "config.market.tw", suffix: ".TW", currency: "TWD" },
  { key: "JP", labelKey: "config.market.jp", suffix: ".T", currency: "JPY" },
  { key: "HK", labelKey: "config.market.hk", suffix: ".HK", currency: "HKD" },
] as const
