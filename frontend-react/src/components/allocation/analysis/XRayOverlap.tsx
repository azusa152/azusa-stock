import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { useXRayAlert } from "@/api/hooks/useAllocation"
import type { XRayEntry } from "@/api/types/allocation"

interface Props {
  xray: XRayEntry[]
}

const XRAY_WARNING_THRESHOLD = 15

export function XRayOverlap({ xray }: Props) {
  const { t } = useTranslation()
  const alertMutation = useXRayAlert()
  const feedback = alertMutation.isSuccess ? t("common.success") : alertMutation.isError ? t("common.error") : null

  const top15 = [...xray].sort((a, b) => b.total_weight_pct - a.total_weight_pct).slice(0, 15)
  const hasWarning = top15.some((e) => e.total_weight_pct > XRAY_WARNING_THRESHOLD)

  if (top15.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.xray.title")}</p>
        <p className="text-sm text-muted-foreground">{t("allocation.xray.empty")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{t("allocation.xray.title")}</p>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          onClick={() => alertMutation.mutate()}
          disabled={alertMutation.isPending}
        >
          {t("allocation.xray.alert_button")}
        </Button>
      </div>

      {hasWarning && (
        <div className="rounded-md border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-xs text-orange-700 dark:text-orange-400">
          {t("allocation.xray.warning", { threshold: XRAY_WARNING_THRESHOLD })}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.xray.col_name")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.xray.col_direct")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.xray.col_indirect")}</th>
              <th className="text-right py-0.5">{t("allocation.xray.col_total")}</th>
            </tr>
          </thead>
          <tbody>
            {top15.map((e, i) => (
              <tr
                key={i}
                className={`border-b border-border/50 ${e.total_weight_pct > XRAY_WARNING_THRESHOLD ? "text-orange-600 dark:text-orange-400" : ""}`}
              >
                <td className="py-0.5 pr-2 font-medium">{e.symbol}</td>
                <td className="py-0.5 pr-2 text-muted-foreground max-w-[120px] truncate">{e.name}</td>
                <td className="py-0.5 pr-2 text-right">{e.direct_weight_pct.toFixed(1)}%</td>
                <td className="py-0.5 pr-2 text-right">{e.indirect_weight_pct.toFixed(1)}%</td>
                <td className="py-0.5 text-right font-semibold">{e.total_weight_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}
