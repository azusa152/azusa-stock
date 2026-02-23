import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useToggleFxWatch, useDeleteFxWatch, useFxHistory } from "@/api/hooks/useFxWatch"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { FxChart } from "./FxChart"
import { EditWatchPopover } from "./EditWatchPopover"
import type { FxWatch, FxAnalysis } from "@/api/types/fxWatch"

interface Props {
  watch: FxWatch
  analysis: FxAnalysis | undefined
  analysisLoading?: boolean
}

export function WatchCard({ watch, analysis, analysisLoading = false }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  const toggle = useToggleFxWatch()
  const del = useDeleteFxWatch()
  const [deleteFeedback, setDeleteFeedback] = useState<string | null>(null)
  const [toggleFeedback, setToggleFeedback] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: historyData } = useFxHistory(watch.base_currency, watch.quote_currency, expanded && !isPrivate)

  const pair = `${watch.base_currency}/${watch.quote_currency}`
  const currentRate = analysis?.current_rate
  const rateStr = currentRate ? currentRate.toFixed(4) : "—"

  const badge = analysis
    ? analysis.should_alert
      ? `🟢 ${analysis.recommendation}`
      : `⚪ ${analysis.recommendation}`
    : analysisLoading
      ? "⏳ …"
      : t("fx_watch.analysis.waiting")

  const statusIcon = watch.is_active ? "🟢" : "🔴"

  const handleToggle = () => {
    toggle.mutate(
      { id: watch.id, isActive: watch.is_active },
      {
        onError: () => setToggleFeedback(t("fx_watch.card.toggle_error")),
      },
    )
  }

  const handleDeleteClick = () => {
    setConfirmDelete(true)
  }

  const handleDeleteConfirm = () => {
    del.mutate(watch.id, {
      onError: () => {
        setDeleteFeedback(t("fx_watch.card.delete_error"))
        setConfirmDelete(false)
      },
    })
  }

  return (
    <Card>
      <CardContent className="p-3">
        {/* Collapsible header */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-full text-left flex items-center justify-between"
        >
          <span className="text-sm font-medium">
            {statusIcon} 💱 {pair} — {rateStr} — {badge}
          </span>
          <span className="text-muted-foreground text-xs">{expanded ? "▲" : "▼"}</span>
        </button>

        {expanded && (
          <div className="mt-3 space-y-3">
            {/* Action row */}
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={handleToggle}
                disabled={toggle.isPending}
              >
                {watch.is_active ? t("fx_watch.card.disable") : t("fx_watch.card.enable")}
              </Button>
              <EditWatchPopover watch={watch} />
              {confirmDelete ? (
                <>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="text-xs"
                    onClick={handleDeleteConfirm}
                    disabled={del.isPending}
                  >
                    {t("common.confirm")}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs"
                    onClick={() => setConfirmDelete(false)}
                  >
                    {t("common.cancel")}
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="destructive"
                  className="text-xs"
                  onClick={handleDeleteClick}
                >
                  {t("fx_watch.card.delete")}
                </Button>
              )}
            </div>
            {toggleFeedback && <p className="text-xs text-destructive">{toggleFeedback}</p>}
            {deleteFeedback && <p className="text-xs text-destructive">{deleteFeedback}</p>}

            {isPrivate ? (
              <p className="text-sm text-muted-foreground">{t("fx_watch.privacy_enabled")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-[3fr_2fr]">
                {/* Left: chart */}
                <div>
                  {historyData ? (
                    <FxChart data={historyData} recentHighDays={watch.recent_high_days} />
                  ) : (
                    <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
                  )}
                </div>

                {/* Right: analysis + settings */}
                <div className="space-y-3 text-xs">
                  {/* Analysis */}
                  <div>
                    <p className="font-medium text-muted-foreground">{t("fx_watch.analysis.title")}</p>
                    {analysisLoading && !analysis ? (
                      <div className="mt-1 space-y-1">
                        <Skeleton className="h-3 w-full" />
                        <Skeleton className="h-3 w-4/5" />
                      </div>
                    ) : (
                      <p className="mt-0.5">
                        {analysis?.reasoning ?? t("fx_watch.analysis.waiting")}
                      </p>
                    )}
                  </div>

                  <hr className="border-border" />

                  {/* Settings */}
                  <div className="space-y-0.5 text-muted-foreground">
                    <p className="font-medium text-foreground">{t("fx_watch.settings.title")}</p>
                    <p>{t("fx_watch.settings.recent_high", { days: watch.recent_high_days })}</p>
                    <p>{t("fx_watch.settings.consecutive", { days: watch.consecutive_increase_days })}</p>
                    <p>{t("fx_watch.settings.interval", { hours: watch.reminder_interval_hours })}</p>
                    <p>{t("fx_watch.settings.high_alert", { icon: watch.alert_on_recent_high ? "✅" : "❌" })}</p>
                    <p>{t("fx_watch.settings.consec_alert", { icon: watch.alert_on_consecutive_increase ? "✅" : "❌" })}</p>
                    {watch.last_alerted_at ? (
                      <p>
                        {t("fx_watch.settings.last_alert_time", {
                          time: new Date(watch.last_alerted_at).toLocaleString(),
                        })}
                      </p>
                    ) : (
                      <p>{t("fx_watch.settings.last_alert_none")}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
