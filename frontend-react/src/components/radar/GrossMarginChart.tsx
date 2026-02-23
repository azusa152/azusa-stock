import { useTranslation } from "react-i18next"
import { LazyPlot as Plot } from "@/components/LazyPlot"
import { usePlotlyTheme } from "@/hooks/usePlotlyTheme"
import type { MoatAnalysis } from "@/api/hooks/useRadar"

interface Props {
  data: MoatAnalysis
}

const MOAT_STATUS_COLOR: Record<string, string> = {
  HEALTHY: "text-green-600 dark:text-green-400",
  DETERIORATING: "text-red-600 dark:text-red-400",
  STABLE: "text-yellow-600 dark:text-yellow-400",
  NOT_AVAILABLE: "text-muted-foreground",
}

export function GrossMarginChart({ data }: Props) {
  const { t } = useTranslation()
  const plotlyTheme = usePlotlyTheme()

  const trend = data.margin_trend?.filter((p) => p.value != null) ?? []

  if (trend.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">{t("radar.stock_card.moat_chart_title")}</p>
        <p className="text-xs text-muted-foreground">{t("chart.insufficient_data")}</p>
      </div>
    )
  }

  const dates = trend.map((p) => p.date)
  const values = trend.map((p) => p.value as number)

  // Color each bar relative to previous bar: green if improved, red if declined
  const barColors = values.map((v, i) => {
    if (i === 0) return "#6b7280"
    return v >= values[i - 1] ? "#22c55e" : "#ef4444"
  })

  const moatColor = MOAT_STATUS_COLOR[data.moat] ?? "text-muted-foreground"

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{t("radar.stock_card.moat_chart_title")}</p>
      <Plot
        data={[
          {
            x: dates,
            y: values,
            type: "bar",
            marker: { color: barColors },
            hovertemplate: "%{x}<br>" + t("chart.gross_margin") + ": %{y:.1f}%<extra></extra>",
          },
        ]}
        layout={{
          height: 160,
          margin: { l: 35, r: 10, t: 4, b: 30 },
          xaxis: { tickfont: { size: 9 }, showgrid: false },
          yaxis: {
            tickfont: { size: 9 },
            ticksuffix: "%",
            showgrid: true,
            gridcolor: "rgba(128,128,128,0.1)",
          },
          ...plotlyTheme,
          font: { ...plotlyTheme.font, size: 10 },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
      {data.details && (
        <p className={`text-xs ${moatColor}`}>{data.details}</p>
      )}
    </div>
  )
}
