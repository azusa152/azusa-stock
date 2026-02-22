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
