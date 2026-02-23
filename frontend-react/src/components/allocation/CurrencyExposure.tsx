import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { LazyPlot as Plot } from "@/components/LazyPlot"
import { useCurrencyExposure, useFxExposureAlert, useUpdateProfile } from "@/api/hooks/useAllocation"
import type { ProfileResponse } from "@/api/types/allocation"
import { DISPLAY_CURRENCIES } from "@/lib/constants"
import { usePlotlyTheme } from "@/hooks/usePlotlyTheme"

interface Props {
  privacyMode: boolean
  profile: ProfileResponse
  enabled: boolean
}

const ALERT_COLORS: Record<string, string> = {
  daily_spike: "#ef4444",
  short_term_swing: "#f59e0b",
  long_term_trend: "#3b82f6",
}

export function CurrencyExposure({ privacyMode, profile, enabled }: Props) {
  const { t } = useTranslation()
  const plotlyTheme = usePlotlyTheme()
  const { data, isLoading } = useCurrencyExposure(enabled)
  const alertMutation = useFxExposureAlert()
  const updateProfileMutation = useUpdateProfile()

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-40" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Skeleton className="h-52 rounded-lg" />
          <Skeleton className="h-52 rounded-lg" />
        </div>
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">{t("common.error")}</p>
  }

  const cashLabels = data.cash_breakdown.map((b) => b.currency)
  const cashValues = data.cash_breakdown.map((b) => b.percentage)
  const totalLabels = data.breakdown.map((b) => b.currency)
  const totalValues = data.breakdown.map((b) => b.percentage)

  const donutLayout = {
    height: 220,
    margin: { l: 0, r: 0, t: 5, b: 0 },
    showlegend: true,
    legend: { orientation: "h" as const, y: -0.15 },
    ...plotlyTheme,
    font: { ...plotlyTheme.font, size: 10 },
  }

  return (
    <div className="space-y-4">
      {/* Home currency selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold">{t("allocation.fx.title")}</span>
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-muted-foreground">{t("allocation.fx.home_currency")}</span>
          <select
            defaultValue={profile.home_currency}
            onChange={(e) => updateProfileMutation.mutate(
            { id: profile.id, payload: { home_currency: e.target.value } },
            {
              onSuccess: () => toast.success(t("common.success")),
              onError: () => toast.error(t("common.error_backend")),
            },
          )}
            className="text-xs border border-border rounded px-2 py-1 bg-background"
          >
            {DISPLAY_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {/* Donut charts */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.fx.cash_chart")}</p>
          {!privacyMode ? (
            <Plot
              data={[{
                type: "pie",
                labels: cashLabels,
                values: cashValues,
                hole: 0.4,
                hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
                textinfo: "label+percent",
              }]}
              layout={donutLayout}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          ) : (
            <div className="h-52 flex items-center justify-center border border-border rounded text-xs text-muted-foreground">
              ***
            </div>
          )}
        </div>
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.fx.total_chart")}</p>
          {!privacyMode ? (
            <Plot
              data={[{
                type: "pie",
                labels: totalLabels,
                values: totalValues,
                hole: 0.4,
                hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
                textinfo: "label+percent",
              }]}
              layout={donutLayout}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          ) : (
            <div className="h-52 flex items-center justify-center border border-border rounded text-xs text-muted-foreground">
              ***
            </div>
          )}
        </div>
      </div>

      {/* FX Movements */}
      {data.fx_movements.length > 0 && (
        <section className="space-y-1">
          <p className="text-sm font-semibold">{t("allocation.fx.movements_title")}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground border-b border-border">
                  <th className="text-left py-0.5 pr-3">{t("allocation.fx.col_pair")}</th>
                  <th className="text-right py-0.5 pr-3">{t("allocation.fx.col_rate")}</th>
                  <th className="text-right py-0.5">{t("allocation.fx.col_change")}</th>
                </tr>
              </thead>
              <tbody>
                {data.fx_movements.map((m, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-0.5 pr-3 font-medium">{m.pair}</td>
                    <td className="py-0.5 pr-3 text-right">{m.current_rate.toFixed(4)}</td>
                    <td
                      className="py-0.5 text-right"
                      style={{ color: m.change_pct >= 0 ? "#22c55e" : "#ef4444" }}
                    >
                      {m.change_pct >= 0 ? "+" : ""}{m.change_pct.toFixed(2)}% {m.direction === "up" ? "📈" : "📉"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Rate Alerts */}
      {data.fx_rate_alerts.length > 0 && (
        <section className="space-y-1">
          <p className="text-sm font-semibold">{t("allocation.fx.alerts_title")}</p>
          <div className="space-y-1">
            {data.fx_rate_alerts.map((a, i) => (
              <div
                key={i}
                className="text-xs flex items-center gap-2"
                style={{ color: ALERT_COLORS[a.alert_type] ?? "#9ca3af" }}
              >
                <span className="font-semibold">{a.pair}</span>
                <span>{a.period_label}</span>
                <span>{a.change_pct >= 0 ? "+" : ""}{a.change_pct.toFixed(2)}%</span>
                <span className="text-muted-foreground">@ {a.current_rate.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Advice */}
      {data.advice.length > 0 && (
        <ul className="space-y-1">
          {data.advice.map((a, i) => (
            <li key={i} className="text-xs text-muted-foreground">• {a}</li>
          ))}
        </ul>
      )}

      {/* Alert button */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          onClick={() => alertMutation.mutate(undefined, {
            onSuccess: () => toast.success(t("common.success")),
            onError: () => toast.error(t("common.error_backend")),
          })}
          disabled={alertMutation.isPending}
        >
          {alertMutation.isPending ? t("common.loading") : t("allocation.fx.alert_button")}
        </Button>
        {alertMutation.isSuccess && <span className="text-xs text-muted-foreground">{t("common.success")}</span>}
        {alertMutation.isError && <span className="text-xs text-destructive">{t("common.error")}</span>}
      </div>
    </div>
  )
}
