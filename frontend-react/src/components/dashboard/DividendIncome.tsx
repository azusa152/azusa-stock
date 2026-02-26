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

  // Note: ytd_dividend_per_share is sourced from yfinance in the stock's native currency.
  // Without FX conversion the total mixes currencies (e.g. USD + JPY + HKD).
  // This is a best-effort estimate valid only for single-currency portfolios or portfolios
  // where most dividends are in the same currency.
  let ytdDivIncome = 0
  const breakdown: { ticker: string; quantity: number; dps: number; subtotal: number }[] = []
  for (const h of rebalance.holdings_detail) {
    const ytdDps = divLookup[h.ticker]
    if (ytdDps) {
      const subtotal = h.quantity * ytdDps
      ytdDivIncome += subtotal
      breakdown.push({ ticker: h.ticker, quantity: h.quantity, dps: ytdDps, subtotal })
    }
  }

  if (ytdDivIncome === 0) return null

  // Use ~ prefix to signal that the total is an approximation:
  // dividend amounts come from yfinance in each stock's native currency and are not FX-converted.
  const approxFormatted = `~${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(ytdDivIncome)}`

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-1">
          <p className="text-xs text-muted-foreground">{t("dashboard.ytd_dividend")}</p>
          <InfoPopover align="start">
            <p className="text-xs font-medium">{t("dashboard.info.dividend_breakdown")}</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="text-left font-normal pr-2">Ticker</th>
                  <th className="text-right font-normal pr-2">{t("dashboard.info.dividend_qty")}</th>
                  <th className="text-right font-normal pr-2">{t("dashboard.info.dividend_dps")}</th>
                  <th className="text-right font-normal">{t("dashboard.info.dividend_subtotal")}</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map((row) => (
                  <tr key={row.ticker}>
                    <td className="font-medium pr-2">{row.ticker}</td>
                    <td className="text-right pr-2 tabular-nums">{row.quantity}</td>
                    <td className="text-right pr-2 tabular-nums">{row.dps.toFixed(4)}</td>
                    <td className="text-right tabular-nums">{row.subtotal.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4} className="pt-1 text-muted-foreground/70 italic">
                    {t("dashboard.info.dividend_currency_note")}
                  </td>
                </tr>
              </tfoot>
            </table>
          </InfoPopover>
        </div>
        <p className="text-2xl font-bold tabular-nums mt-1">
          {isPrivate ? "***" : approxFormatted}
        </p>
        <p className="text-xs text-muted-foreground mt-1">{t("dashboard.ytd_dividend_actual")}</p>
      </CardContent>
    </Card>
  )
}
