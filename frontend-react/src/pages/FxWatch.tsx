import { useState, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { formatLocalTime, parseUtc } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  useFxWatches,
  useFxAnalysis,
  useCheckFxWatches,
  useAlertFxWatches,
  useFxHistoryMap,
} from "@/api/hooks/useFxWatch"
import { WatchCard } from "@/components/fxwatch/WatchCard"
import { AddWatchDialog } from "@/components/fxwatch/AddWatchDialog"
import type { FxWatch } from "@/api/types/fxWatch"

type SortMode = "alert_first" | "alphabetical" | "volatility"
type FilterMode = "all" | "active_only"

/** Returns absolute (unsigned) % change — used for volatility sort. */
function computeAbsChangePct(history: { close: number }[]): number | null {
  if (history.length < 2) return null
  const first = history[0].close
  const last = history[history.length - 1].close
  if (first <= 0) return null
  return Math.abs((last - first) / first) * 100
}

export default function FxWatch() {
  const { t } = useTranslation()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [sortMode, setSortMode] = useState<SortMode>("alert_first")
  const [filterMode, setFilterMode] = useState<FilterMode>("all")

  const { data: watches, isLoading, isError } = useFxWatches()
  const hasWatches = (watches?.length ?? 0) > 0
  const { data: analysisMap = {}, isLoading: analysisLoading } = useFxAnalysis(hasWatches)
  const checkMutation = useCheckFxWatches()
  const alertMutation = useAlertFxWatches()

  // Eagerly fetch history for all pairs (sparklines)
  const pairs = useMemo(
    () => (watches ?? []).map((w) => ({ base: w.base_currency, quote: w.quote_currency })),
    [watches],
  )
  const { data: historyMap = {} } = useFxHistoryMap(pairs)

  // Summary stats
  const activeCount = watches?.filter((w) => w.is_active).length ?? 0
  const alertCount = Object.values(analysisMap).filter((a) => a.should_alert).length
  const lastAlertTimes = (watches ?? [])
    .map((w) => w.last_alerted_at)
    .filter((ts): ts is string => ts !== null)
  const lastAlert =
    lastAlertTimes.length > 0
      ? formatLocalTime(lastAlertTimes.reduce((a, b) => (parseUtc(a) > parseUtc(b) ? a : b)))
      : null

  const handleCheck = () => {
    checkMutation.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: () => toast.error(t("common.error")),
    })
  }

  const handleAlert = () => {
    alertMutation.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: () => toast.error(t("common.error")),
    })
  }

  // Filter
  const filteredWatches = useMemo(() => {
    if (!watches) return []
    if (filterMode === "active_only") return watches.filter((w) => w.is_active)
    return watches
  }, [watches, filterMode])

  // Sort
  const sortedWatches = useMemo(() => {
    const list = [...filteredWatches]
    if (sortMode === "alert_first") {
      list.sort((a, b) => {
        const aAlert = analysisMap[a.id]?.should_alert ? 1 : 0
        const bAlert = analysisMap[b.id]?.should_alert ? 1 : 0
        if (bAlert !== aAlert) return bAlert - aAlert
        // secondary: active first
        return (b.is_active ? 1 : 0) - (a.is_active ? 1 : 0)
      })
    } else if (sortMode === "alphabetical") {
      list.sort((a, b) => {
        const pairA = `${a.base_currency}/${a.quote_currency}`
        const pairB = `${b.base_currency}/${b.quote_currency}`
        return pairA.localeCompare(pairB)
      })
    } else if (sortMode === "volatility") {
      list.sort((a, b) => {
        const pairA = `${a.base_currency}/${a.quote_currency}`
        const pairB = `${b.base_currency}/${b.quote_currency}`
        const histA = historyMap[pairA] ?? []
        const histB = historyMap[pairB] ?? []
        const volA = computeAbsChangePct(histA.slice(-30)) ?? 0
        const volB = computeAbsChangePct(histB.slice(-30)) ?? 0
        return volB - volA
      })
    }
    return list
  }, [filteredWatches, sortMode, analysisMap, historyMap])

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-72" />
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (isError || !watches) {
    return (
      <div className="p-6 space-y-3">
        <h1 className="text-2xl font-bold">{t("fx_watch.title")}</h1>
        <p className="text-sm text-destructive">{t("common.error_backend")}</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      {/* Toolbar row */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{t("fx_watch.title")}</h1>
            {/* SOP info popover */}
            <Popover>
              <PopoverTrigger asChild>
                <button className="rounded-full w-5 h-5 text-xs border border-border text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center">
                  ?
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-96 max-h-96 overflow-y-auto text-xs" align="start">
                <p className="font-semibold mb-2">{t("fx_watch.sop_title")}</p>
                <div className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {t("fx_watch.sop_content")}
                </div>
              </PopoverContent>
            </Popover>
          </div>
          <p className="text-sm text-muted-foreground">{t("fx_watch.caption")}</p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCheck}
            disabled={checkMutation.isPending || watches.length === 0}
          >
            {checkMutation.isPending ? t("fx_watch.action.analyzing") : t("fx_watch.action.check")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleAlert}
            disabled={alertMutation.isPending || watches.length === 0}
          >
            {alertMutation.isPending ? t("fx_watch.action.sending") : t("fx_watch.action.alert")}
          </Button>
          <Button size="sm" onClick={() => setDialogOpen(true)}>
            {t("fx_watch.action.add")}
          </Button>
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <SummaryCard label={t("fx_watch.metric.total")} value={String(watches.length)} />
        <SummaryCard label={t("fx_watch.metric.active")} value={String(activeCount)} />
        <SummaryCard
          label={t("fx_watch.metric.alerts")}
          value={String(alertCount)}
          highlight={alertCount > 0}
        />
        <SummaryCard
          label={t("fx_watch.metric.last_alert")}
          value={lastAlert ?? t("fx_watch.metric.not_sent")}
          small
        />
      </div>

      {/* Watch list */}
      {watches.length === 0 ? (
        <div className="space-y-1 py-4">
          <p className="text-sm text-muted-foreground">{t("fx_watch.empty.message")}</p>
          <p className="text-xs text-muted-foreground">{t("fx_watch.empty.hint")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Sort & filter controls */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex rounded-md border border-border overflow-hidden">
              <button
                onClick={() => setFilterMode("all")}
                className={`px-3 py-1 text-xs transition-colors ${
                  filterMode === "all"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {t("fx_watch.filter.all")}
              </button>
              <button
                onClick={() => setFilterMode("active_only")}
                className={`px-3 py-1 text-xs border-l border-border transition-colors ${
                  filterMode === "active_only"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {t("fx_watch.filter.active_only")}
              </button>
            </div>

            <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
              <SelectTrigger className="h-7 w-36 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="alert_first" className="text-xs">
                  {t("fx_watch.sort.alert_first")}
                </SelectItem>
                <SelectItem value="alphabetical" className="text-xs">
                  {t("fx_watch.sort.alphabetical")}
                </SelectItem>
                <SelectItem value="volatility" className="text-xs">
                  {t("fx_watch.sort.volatility")}
                </SelectItem>
              </SelectContent>
            </Select>

            <span className="text-xs text-muted-foreground">
              {t("fx_watch.list.title")} ({sortedWatches.length})
            </span>
          </div>

          {sortedWatches.map((watch: FxWatch) => {
            const pair = `${watch.base_currency}/${watch.quote_currency}`
            return (
              <WatchCard
                key={watch.id}
                watch={watch}
                analysis={analysisMap[watch.id]}
                analysisLoading={analysisLoading}
                sparklineData={historyMap[pair]}
              />
            )
          })}
        </div>
      )}

      <AddWatchDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  )
}

interface SummaryCardProps {
  label: string
  value: string
  highlight?: boolean
  small?: boolean
}

function SummaryCard({ label, value, highlight = false, small = false }: SummaryCardProps) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={`${small ? "text-sm font-semibold truncate" : "text-2xl font-bold"} ${
          highlight ? "text-destructive" : ""
        }`}
      >
        {value}
      </p>
    </div>
  )
}
