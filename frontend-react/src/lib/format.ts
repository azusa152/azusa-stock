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
