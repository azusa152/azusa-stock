import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { InfoPopover } from "./InfoPopover"
import type { RebalanceResponse, EnrichedStock } from "@/api/types/dashboard"

interface Props {
  rebalance?: RebalanceResponse | null
  enrichedStocks?: EnrichedStock[]
}

export function DividendIncome({ rebalance, enrichedStocks = [] }: Props) {
  const { t } = useTranslation()
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  if (!rebalance || !enrichedStocks.length) return null

  const currency = rebalance.display_currency ?? "USD"

  // Build per-ticker ytd_dividend_per_share map
  const divLookup: Record<string, number> = {}
  for (const es of enrichedStocks) {
    const ytdDps = es.dividend?.ytd_dividend_per_share
    if (ytdDps != null && ytdDps > 0 && es.ticker) {
      divLookup[es.ticker] = ytdDps
    }
  }

  // ytd_dividend_per_share is in the stock's native currency (from yfinance).
  // current_fx_rate on each HoldingDetail is the same rate the rebalance service used to convert
  // that holding's currency → display_currency, so multiplying gives a properly converted total.
  let ytdDivIncome = 0
  const breakdown: {
    ticker: string
    quantity: number
    nativeDps: number
    nativeSubtotal: number
    convertedSubtotal: number
    nativeCurrency: string
  }[] = []

  for (const h of rebalance.holdings_detail) {
    const nativeDps = divLookup[h.ticker]
    if (nativeDps) {
      const fx = h.current_fx_rate ?? 1.0
      const nativeSubtotal = h.quantity * nativeDps
      const convertedSubtotal = nativeSubtotal * fx
      ytdDivIncome += convertedSubtotal
      breakdown.push({
        ticker: h.ticker,
        quantity: h.quantity,
        nativeDps,
        nativeSubtotal,
        convertedSubtotal,
        nativeCurrency: h.currency ?? "USD",
      })
    }
  }

  if (ytdDivIncome === 0) return null

  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(ytdDivIncome)

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-1">
          <p className="text-xs text-muted-foreground">{t("dashboard.ytd_dividend")}</p>
          <InfoPopover align="start">
            <p className="text-xs font-medium">{t("dashboard.info.dividend_breakdown", { currency })}</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="text-left font-normal pr-2">Ticker</th>
                  <th className="text-right font-normal pr-2">{t("dashboard.info.dividend_dps")}</th>
                  <th className="text-right font-normal pr-2">{t("dashboard.info.dividend_native")}</th>
                  <th className="text-right font-normal">{t("dashboard.info.dividend_converted")}</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map((row) => {
                  const fmtNative = (v: number) =>
                    new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: row.nativeCurrency,
                      minimumFractionDigits: 2,
                    }).format(v)
                  return (
                    <tr key={row.ticker}>
                      <td className="font-medium pr-2">{row.ticker}</td>
                      <td className="text-right pr-2 tabular-nums">{fmtNative(row.nativeDps)}</td>
                      <td className="text-right pr-2 tabular-nums">{fmtNative(row.nativeSubtotal)}</td>
                      <td className="text-right tabular-nums">
                        {new Intl.NumberFormat("en-US", {
                          style: "currency",
                          currency,
                          minimumFractionDigits: 2,
                        }).format(row.convertedSubtotal)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </InfoPopover>
        </div>
        <p className="text-2xl font-bold tabular-nums mt-1">
          {isPrivate ? "***" : formatted}
        </p>
        <p className="text-xs text-muted-foreground mt-1">{t("dashboard.ytd_dividend_actual")}</p>
      </CardContent>
    </Card>
  )
}
