import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useSyncGuru } from "@/api/hooks/useSmartMoney"
import { formatValue, isStale } from "./formatters"
import type { GuruSummaryItem } from "@/api/types/smartMoney"

interface Props {
  gurus: GuruSummaryItem[]
}

export function GuruStatusCards({ gurus }: Props) {
  const { t } = useTranslation()
  const syncMutation = useSyncGuru()

  if (gurus.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("smart_money.overview.no_data")}</p>
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {gurus.map((guru) => {
        const stale = isStale(guru.latest_report_date)
        const syncing = syncMutation.isPending && syncMutation.variables === guru.id

        return (
          <Card key={guru.id} className="relative">
            <CardContent className="p-3 space-y-1.5">
              {/* Header row */}
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold text-sm truncate">{guru.display_name}</p>
                <span className="text-xs shrink-0">
                  {stale
                    ? t("smart_money.overview.stale_label")
                    : t("smart_money.overview.recent_label")}
                </span>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                <div>
                  <span className="block text-foreground font-medium">
                    {formatValue(guru.total_value)}
                  </span>
                  {t("smart_money.overview.total_value_label")}
                </div>
                <div>
                  <span className="block text-foreground font-medium">{guru.holdings_count}</span>
                  {t("smart_money.overview.holdings_count_label")}
                </div>
                <div>
                  <span className="block text-foreground font-medium">{guru.filing_count}</span>
                  {t("smart_money.overview.filing_count_label")}
                </div>
                <div>
                  <span className="block text-foreground font-medium">
                    {guru.latest_report_date ?? "—"}
                  </span>
                  {t("smart_money.overview.report_date_label")}
                </div>
              </div>

              {/* Sync button */}
              <Button
                size="sm"
                variant="outline"
                className="w-full text-xs mt-1"
                onClick={() => syncMutation.mutate(guru.id)}
                disabled={syncMutation.isPending}
              >
                {syncing ? t("smart_money.sidebar.syncing") : t("smart_money.overview.sync_button")}
              </Button>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
