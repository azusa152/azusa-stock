import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  useStocks,
  useEnrichedStocks,
  useLastScan,
  useHoldings,
  useRebalance,
  useProfile,
  useFearGreed,
  useSnapshots,
  useTwr,
  useGreatMinds,
} from "@/api/hooks/useDashboard"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { PortfolioPulse } from "@/components/dashboard/PortfolioPulse"
import { PerformanceChart } from "@/components/dashboard/PerformanceChart"
import { SignalAlerts } from "@/components/dashboard/SignalAlerts"
import { AllocationGlance } from "@/components/dashboard/AllocationGlance"
import { TopHoldings } from "@/components/dashboard/TopHoldings"
import { DividendIncome } from "@/components/dashboard/DividendIncome"
import { ResonanceSummary } from "@/components/dashboard/ResonanceSummary"

const DISPLAY_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "HKD"]

export default function Dashboard() {
  const { t } = useTranslation()
  const [displayCurrency, setDisplayCurrency] = useState("USD")

  const { data: stocks, isLoading: stocksLoading } = useStocks()
  const { data: enrichedStocks } = useEnrichedStocks()
  const { data: lastScan } = useLastScan()
  const { data: holdings } = useHoldings()
  const { data: rebalance, isLoading: rebalanceLoading } = useRebalance(displayCurrency)
  const { data: profile } = useProfile()
  const { data: fearGreed } = useFearGreed()
  const { data: snapshots } = useSnapshots(730)
  const { data: twr } = useTwr()
  const { data: greatMinds, isLoading: greatMindsLoading } = useGreatMinds()

  const heroLoading = stocksLoading || rebalanceLoading

  // Onboarding: no data at all
  if (!stocksLoading && !rebalanceLoading && !stocks?.length && !rebalance) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="text-2xl font-bold">{t("dashboard.title")}</h1>
        <p className="text-muted-foreground">{t("dashboard.welcome")}</p>
      </div>
    )
  }

  // Timestamps
  const priceTs = rebalance?.calculated_at
    ? new Date(rebalance.calculated_at).toLocaleString()
    : null
  const scanTs = lastScan?.last_scanned_at
    ? new Date(lastScan.last_scanned_at).toLocaleString()
    : null

  return (
    <div className="p-6 space-y-6">
      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold flex-1">{t("dashboard.title")}</h1>
        <Select value={displayCurrency} onValueChange={setDisplayCurrency}>
          <SelectTrigger className="w-28 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DISPLAY_CURRENCY_OPTIONS.map((c) => (
              <SelectItem key={c} value={c} className="text-xs">
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Timestamps */}
      {(priceTs || scanTs) && (
        <p className="text-xs text-muted-foreground -mt-4">
          {[
            priceTs && t("dashboard.price_updated", { timestamp: priceTs }),
            scanTs && t("dashboard.last_scan", { timestamp: scanTs }),
          ]
            .filter(Boolean)
            .join(" ｜ ")}
        </p>
      )}

      {/* Portfolio Pulse hero */}
      <PortfolioPulse
        rebalance={rebalance}
        fearGreed={fearGreed}
        twr={twr}
        snapshots={snapshots ?? []}
        lastScan={lastScan}
        stocks={stocks ?? []}
        enrichedStocks={enrichedStocks ?? []}
        holdings={holdings ?? []}
        isLoading={heroLoading}
      />

      {/* YTD Dividend Income */}
      <DividendIncome rebalance={rebalance} enrichedStocks={enrichedStocks ?? []} />

      {/* Performance Chart */}
      <PerformanceChart snapshots={snapshots ?? []} />

      {/* Signal Alerts */}
      <SignalAlerts
        stocks={stocks ?? []}
        enrichedStocks={enrichedStocks ?? []}
        rebalance={rebalance}
      />

      {/* Allocation at a Glance */}
      <AllocationGlance rebalance={rebalance} profile={profile} />

      {/* Top Holdings */}
      <TopHoldings rebalance={rebalance} />

      {/* Smart Money Resonance */}
      <ResonanceSummary greatMinds={greatMinds} isLoading={greatMindsLoading} />
    </div>
  )
}
