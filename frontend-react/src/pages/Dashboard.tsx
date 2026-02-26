import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { SendHorizonal } from "lucide-react"
import { formatLocalTime } from "@/lib/utils"
import {
  useStocks,
  useEnrichedStocks,
  useLastScan,
  useHoldings,
  useRebalance,
  useProfile,
  useSignalActivity,
  useFearGreed,
  useSnapshots,
  useTwr,
  useGreatMinds,
} from "@/api/hooks/useDashboard"
import { useTriggerDigest } from "@/api/hooks/useAllocation"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { LazySection } from "@/components/LazySection"
import { PortfolioPulse } from "@/components/dashboard/PortfolioPulse"
import { PerformanceChart } from "@/components/dashboard/PerformanceChart"
import { SignalAlerts } from "@/components/dashboard/SignalAlerts"
import { AllocationGlance } from "@/components/dashboard/AllocationGlance"
import { TopHoldings } from "@/components/dashboard/TopHoldings"
import { DividendIncome } from "@/components/dashboard/DividendIncome"
import { ResonanceSummary } from "@/components/dashboard/ResonanceSummary"
import { StockHeatmap } from "@/components/dashboard/StockHeatmap"

const DISPLAY_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "HKD"]

export default function Dashboard() {
  const { t } = useTranslation()
  const [displayCurrency, setDisplayCurrency] = useState("USD")
  const digestMutation = useTriggerDigest()

  const handleDigest = () => {
    digestMutation.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: () => toast.error(t("common.error")),
    })
  }

  // Fast (DB-only) queries — fired immediately on mount.
  const { data: stocks, isLoading: stocksLoading } = useStocks()
  const { data: holdings } = useHoldings()
  const { data: lastScan } = useLastScan()
  const { data: signalActivity } = useSignalActivity()
  const { data: snapshots, isLoading: snapshotsLoading } = useSnapshots(730)
  const { data: twr } = useTwr()
  const { data: profile } = useProfile()

  // useRebalance fires immediately (not gated) because heroLoading and PortfolioPulse
  // both depend on it. Its response is cached on the backend (60s TTL) so repeat
  // requests are fast; placeholderData keeps old data visible on currency switch.
  const { data: rebalance, isLoading: rebalanceLoading } = useRebalance(displayCurrency)

  // Heavy yfinance queries — gated behind stocksLoading so the fast DB-only
  // requests above can claim FastAPI threadpool workers first. Note: LazySection
  // below defers *rendering* of below-fold components, but these hooks are still
  // registered here; data fetching starts as soon as stocksLoading resolves.
  const { data: enrichedStocks, isLoading: enrichedLoading } = useEnrichedStocks({
    enabled: !stocksLoading,
  })
  const { data: fearGreed } = useFearGreed({ enabled: !stocksLoading })
  const { data: greatMinds, isLoading: greatMindsLoading } = useGreatMinds({
    enabled: !stocksLoading,
  })

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
    ? formatLocalTime(rebalance.calculated_at)
    : null
  const scanTs = lastScan?.last_scanned_at
    ? formatLocalTime(lastScan.last_scanned_at)
    : null

  return (
    <div className="p-6 space-y-6">
      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-2xl font-bold flex-1">{t("dashboard.title")}</h1>
        <Button
          size="sm"
          variant="outline"
          className="text-xs gap-1.5"
          onClick={handleDigest}
          disabled={digestMutation.isPending}
          title={t("dashboard.digest_tooltip")}
        >
          <SendHorizonal className="w-3.5 h-3.5" />
          {t("dashboard.digest_tooltip")}
        </Button>
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

      {/* Stock Heat Map */}
      <StockHeatmap enrichedStocks={enrichedStocks ?? []} isLoading={enrichedLoading} />

      {/* YTD Dividend Income */}
      <DividendIncome rebalance={rebalance} enrichedStocks={enrichedStocks ?? []} />

      {/* Performance Chart */}
      <PerformanceChart snapshots={snapshots ?? []} isLoading={snapshotsLoading} />

      {/* Signal Alerts — lazy loaded (below fold) */}
      <LazySection fallback={<Card><CardContent className="p-6"><Skeleton className="h-24 w-full" /></CardContent></Card>}>
        <SignalAlerts
          stocks={stocks ?? []}
          enrichedStocks={enrichedStocks ?? []}
          rebalance={rebalance}
          signalActivity={signalActivity ?? []}
        />
      </LazySection>

      {/* Allocation at a Glance — lazy loaded (below fold) */}
      <LazySection fallback={<Card><CardContent className="p-6"><Skeleton className="h-[200px] w-full" /></CardContent></Card>}>
        <AllocationGlance rebalance={rebalance} profile={profile} isLoading={heroLoading} />
      </LazySection>

      {/* Top Holdings — lazy loaded (below fold) */}
      <LazySection fallback={<Card><CardContent className="p-6"><Skeleton className="h-32 w-full" /></CardContent></Card>}>
        <TopHoldings rebalance={rebalance} />
      </LazySection>

      {/* Smart Money Resonance — lazy loaded (below fold) */}
      <LazySection fallback={<Card><CardContent className="p-6"><Skeleton className="h-24 w-full" /></CardContent></Card>}>
        <ResonanceSummary greatMinds={greatMinds} isLoading={greatMindsLoading} />
      </LazySection>
    </div>
  )
}
