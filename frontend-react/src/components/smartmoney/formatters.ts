export function formatValue(v: number | null | undefined): string {
  if (v == null) return "N/A"
  if (v >= 1_000_000_000) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1_000_000) return `$${(v / 1e6).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1e3).toFixed(1)}K`
  return `$${v.toFixed(0)}`
}

export function formatShares(s: number | null | undefined): string {
  if (s == null) return "N/A"
  if (s >= 1_000_000) return `${(s / 1e6).toFixed(2)}M`
  if (s >= 1_000) return `${(s / 1e3).toFixed(1)}K`
  return `${s.toFixed(0)}`
}

export const SMART_MONEY_STALE_DAYS = 120

export function isStale(reportDate: string | null | undefined): boolean {
  if (!reportDate) return true
  const d = new Date(reportDate)
  const now = new Date()
  const diffDays = (now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24)
  return diffDays > SMART_MONEY_STALE_DAYS
}

export const ACTION_COLORS: Record<string, string> = {
  NEW_POSITION: "#22c55e",
  SOLD_OUT: "#ef4444",
  INCREASED: "#3b82f6",
  DECREASED: "#f59e0b",
  UNCHANGED: "#9ca3af",
}

export const ACTION_ICONS: Record<string, string> = {
  NEW_POSITION: "🟢",
  SOLD_OUT: "🔴",
  INCREASED: "🔵",
  DECREASED: "🟡",
  UNCHANGED: "⚪",
}
