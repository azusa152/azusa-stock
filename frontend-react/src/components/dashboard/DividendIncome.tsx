import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import type { RebalanceResponse, EnrichedStock } from "@/api/types/dashboard"

interface Props {
  rebalance?: RebalanceResponse | null
  enrichedStocks?: EnrichedStock[]
}

export function DividendIncome({ rebalance, enrichedStocks = [] }: Props) {
  const { t } = useTranslation()
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  if (!rebalance || !enrichedStocks.length) return null

  // Build per-ticker ytd_dividend_per_share map
  const divLookup: Record<string, number> = {}
  for (const es of enrichedStocks) {
    const ytdDps = es.dividend?.ytd_dividend_per_share
    if (ytdDps != null && ytdDps > 0 && es.ticker) {
      divLookup[es.ticker] = ytdDps
    }
  }

  // TODO: ytd_dividend_per_share is sourced from yfinance in the stock's native currency.
  // Without FX conversion the total mixes currencies (e.g. USD + JPY + HKD).
  // A proper fix requires the backend to provide per-holding FX rates or pre-convert to
  // display_currency. For now this is a best-effort estimate valid only for single-currency
  // portfolios or portfolios where most dividends are in the same currency.
  let ytdDivIncome = 0
  for (const h of rebalance.holdings_detail) {
    const ytdDps = divLookup[h.ticker]
    if (ytdDps) {
      ytdDivIncome += h.quantity * ytdDps
    }
  }

  if (ytdDivIncome === 0) return null

  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{t("dashboard.ytd_dividend")}</p>
        <p className="text-2xl font-bold tabular-nums mt-1">
          {isPrivate ? "***" : `$${ytdDivIncome.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
        </p>
        <p className="text-xs text-muted-foreground mt-1">{t("dashboard.ytd_dividend_actual")}</p>
      </CardContent>
    </Card>
  )
}
