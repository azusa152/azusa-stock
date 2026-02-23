import { useState } from "react"
import { useTranslation } from "react-i18next"
import { formatLocalTime, parseUtc } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useFxWatches,
  useFxAnalysis,
  useCheckFxWatches,
  useAlertFxWatches,
} from "@/api/hooks/useFxWatch"
import { WatchCard } from "@/components/fxwatch/WatchCard"
import { AddWatchDialog } from "@/components/fxwatch/AddWatchDialog"

export default function FxWatch() {
  const { t } = useTranslation()
  const [sopOpen, setSopOpen] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [checkFeedback, setCheckFeedback] = useState<string | null>(null)
  const [alertFeedback, setAlertFeedback] = useState<string | null>(null)

  const { data: watches, isLoading, isError } = useFxWatches()
  const hasWatches = (watches?.length ?? 0) > 0
  const { data: analysisMap = {}, isLoading: analysisLoading } = useFxAnalysis(hasWatches)
  const checkMutation = useCheckFxWatches()
  const alertMutation = useAlertFxWatches()

  const activeCount = watches?.filter((w) => w.is_active).length ?? 0
  const lastAlertTimes = (watches ?? [])
    .map((w) => w.last_alerted_at)
    .filter((ts): ts is string => ts !== null)
  const lastAlert =
    lastAlertTimes.length > 0
      ? formatLocalTime(
          lastAlertTimes.reduce((a, b) => (parseUtc(a) > parseUtc(b) ? a : b)),
        )
      : null

  const handleCheck = () => {
    setCheckFeedback(null)
    checkMutation.mutate(undefined, {
      onSuccess: () => setCheckFeedback(t("common.success")),
      onError: () => setCheckFeedback(t("common.error")),
    })
  }

  const handleAlert = () => {
    setAlertFeedback(null)
    alertMutation.mutate(undefined, {
      onSuccess: () => setAlertFeedback(t("common.success")),
      onError: () => setAlertFeedback(t("common.error")),
    })
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-72" />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
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
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">{t("fx_watch.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("fx_watch.caption")}</p>
      </div>

      {/* SOP collapsible */}
      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          className="w-full text-left px-4 py-2 text-sm font-medium hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("fx_watch.sop_title")}</span>
          <span className="text-muted-foreground text-xs">{sopOpen ? "▲" : "▼"}</span>
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("fx_watch.sop_content")}
            </div>
          </div>
        )}
      </div>

      {/* KPI row + action buttons */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
        <div className="rounded-lg border border-border p-3">
          <p className="text-xs text-muted-foreground">{t("fx_watch.metric.total")}</p>
          <p className="text-2xl font-bold">{watches.length}</p>
        </div>
        <div className="rounded-lg border border-border p-3">
          <p className="text-xs text-muted-foreground">{t("fx_watch.metric.active")}</p>
          <p className="text-2xl font-bold">{activeCount}</p>
        </div>
        <div className="rounded-lg border border-border p-3">
          <p className="text-xs text-muted-foreground">{t("fx_watch.metric.last_alert")}</p>
          <p className="text-sm font-semibold truncate">
            {lastAlert ?? t("fx_watch.metric.not_sent")}
          </p>
        </div>

        <Button
          size="sm"
          variant="outline"
          className="h-full text-xs"
          onClick={handleCheck}
          disabled={checkMutation.isPending || watches.length === 0}
        >
          {checkMutation.isPending ? t("fx_watch.action.analyzing") : t("fx_watch.action.check")}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-full text-xs"
          onClick={handleAlert}
          disabled={alertMutation.isPending || watches.length === 0}
        >
          {alertMutation.isPending ? t("fx_watch.action.sending") : t("fx_watch.action.alert")}
        </Button>
        <Button
          size="sm"
          className="h-full text-xs"
          onClick={() => setDialogOpen(true)}
        >
          {t("fx_watch.action.add")}
        </Button>
      </div>

      {checkFeedback && <p className="text-xs text-muted-foreground">{checkFeedback}</p>}
      {alertFeedback && <p className="text-xs text-muted-foreground">{alertFeedback}</p>}

      {/* Watch list */}
      {watches.length === 0 ? (
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{t("fx_watch.empty.message")}</p>
          <p className="text-xs text-muted-foreground">{t("fx_watch.empty.hint")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-semibold">{t("fx_watch.list.title")}</p>
          {watches.map((watch) => (
            <WatchCard
              key={watch.id}
              watch={watch}
              analysis={analysisMap[watch.id]}
              analysisLoading={analysisLoading}
            />
          ))}
        </div>
      )}

      <AddWatchDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  )
}
