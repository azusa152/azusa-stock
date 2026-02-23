import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { formatLocalTime } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { useLastScan } from "@/api/hooks/useDashboard"
import {
  useRadarStocks,
  useRadarEnrichedStocks,
  useRemovedStocks,
  useScanStatus,
  useResonance,
} from "@/api/hooks/useRadar"
import { CategoryTabs } from "@/components/radar/CategoryTabs"
import { AddStockDrawer } from "@/components/radar/AddStockDrawer"
import type { RadarEnrichedStock } from "@/api/types/radar"

export default function Radar() {
  const { t } = useTranslation()
  const [sopOpen, setSopOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data: stocks, isLoading: stocksLoading, isError: stocksError } = useRadarStocks()
  const { data: enrichedStocks } = useRadarEnrichedStocks()
  const { data: removedStocks } = useRemovedStocks()
  const { data: lastScan } = useLastScan()
  const { data: scanStatus } = useScanStatus()
  const { data: resonanceMap } = useResonance()

  const isScanning = scanStatus?.is_running ?? false

  // Build enriched map: ticker → enriched data
  const enrichedMap: Record<string, RadarEnrichedStock> = {}
  for (const es of enrichedStocks ?? []) {
    if (es.ticker) enrichedMap[es.ticker] = es
  }

  if (stocksLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="mt-1 h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-28" />
        </div>
        <Skeleton className="h-10 w-full" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (stocksError || !stocks) {
    return (
      <div className="p-6 space-y-3">
        <h1 className="text-2xl font-bold">{t("radar.title")}</h1>
        <p className="text-sm text-destructive">{t("radar.loading.error")}</p>
        <p className="text-xs text-muted-foreground">{t("radar.loading.error_hint")}</p>
      </div>
    )
  }

  const scanTs = lastScan?.last_scanned_at
    ? formatLocalTime(lastScan.last_scanned_at)
    : null

  return (
    <div className="p-6 space-y-4">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{t("radar.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("radar.caption")}</p>
        </div>
        <div className="flex items-center gap-2">
          {isScanning && (
            <span className="text-xs text-amber-500 animate-pulse">{t("radar.scan.running")}</span>
          )}
          <Button size="sm" variant="outline" onClick={() => setDrawerOpen(true)}>
            {t("radar.panel_header")}
          </Button>
        </div>
      </div>

      {/* SOP collapsible */}
      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          className="w-full text-left px-4 py-2 text-sm font-medium hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("radar.sop.title")}</span>
          <span className="text-muted-foreground text-xs">{sopOpen ? "▲" : "▼"}</span>
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("radar.sop.content")}
            </div>
          </div>
        )}
      </div>

      {/* Data freshness */}
      <p className="text-xs text-muted-foreground -mt-2">
        {scanTs
          ? t("radar.last_scan_time", { time: scanTs })
          : t("radar.no_scan_yet")}
        {" · "}
        {t("radar.loading.success", { count: stocks.filter((s) => s.is_active).length })}
      </p>

      {/* Category tabs */}
      <CategoryTabs
        stocks={stocks}
        removedStocks={removedStocks ?? []}
        enrichedMap={enrichedMap}
        resonanceMap={resonanceMap ?? {}}
      />

      {/* Control panel drawer */}
      <AddStockDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        isScanning={isScanning}
      />
    </div>
  )
}
