import { MARKET_HOURS } from "@/lib/constants"

const JPY_FORMATTER = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 0,
})

const DEFAULT_FORMATTER = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/**
 * Format a price with currency-appropriate decimals.
 * JPY: no decimals, thousands separator (1,234)
 * TWD: no decimals, thousands separator (1,234)
 * Others: 2 decimals (1,234.56)
 */
export function formatPrice(value: number, currencyCode: string): string {
  if (currencyCode === "JPY" || currencyCode === "TWD") {
    return JPY_FORMATTER.format(value)
  }
  return DEFAULT_FORMATTER.format(value)
}

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number)
  return h * 60 + m
}

export function isMarketOpen(marketKey: string): boolean {
  const hours = MARKET_HOURS[marketKey]
  if (!hours) return false

  const now = new Date()
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: hours.tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    weekday: "short",
  })
  const parts = formatter.formatToParts(now)
  const weekday = parts.find((p) => p.type === "weekday")?.value
  if (weekday === "Sat" || weekday === "Sun") return false

  const hhmm = parts
    .filter((p) => p.type === "hour" || p.type === "minute")
    .map((p) => p.value)
    .join(":")
  const currentMinutes = toMinutes(hhmm)
  const openMin = toMinutes(hours.open)
  const closeMin = toMinutes(hours.close)

  if (currentMinutes < openMin || currentMinutes >= closeMin) return false
  if (hours.lunch) {
    const [lunchStart, lunchEnd] = hours.lunch
    if (currentMinutes >= toMinutes(lunchStart) && currentMinutes < toMinutes(lunchEnd)) return false
  }
  return true
}
