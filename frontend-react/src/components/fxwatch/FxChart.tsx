import { useState, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { LazyPlot as Plot } from "@/components/LazyPlot"
import type { FxHistoryPoint } from "@/api/types/fxWatch"
import { usePlotlyTheme } from "@/hooks/usePlotlyTheme"

const PERIOD_OPTIONS = [
  { key: "1M", days: 30 },
  { key: "2M", days: 60 },
  { key: "3M", days: 90 },
]

interface Props {
  data: FxHistoryPoint[]
  recentHighDays: number
}

export function FxChart({ data, recentHighDays }: Props) {
  const { t } = useTranslation()
  const plotlyTheme = usePlotlyTheme()
  const [period, setPeriod] = useState("3M")

  const sliced = useMemo(() => {
    const n = PERIOD_OPTIONS.find((p) => p.key === period)?.days ?? 90
    return data.length >= n ? data.slice(-n) : data
  }, [data, period])

  if (!data || data.length < 5) {
    return <p className="text-xs text-muted-foreground">{t("fx_watch.chart.insufficient_data")}</p>
  }

  const dates = sliced.map((d) => d.date)
  const rates = sliced.map((d) => d.close)
  const isUp = rates[rates.length - 1] >= rates[0]
  const lineColor = isUp ? "#00C805" : "#FF5252"
  const fillColor = isUp ? "rgba(0,200,5,0.1)" : "rgba(255,82,82,0.1)"

  const yMin = Math.min(...rates)
  const yMax = Math.max(...rates)
  const padding = yMax > yMin ? (yMax - yMin) * 0.05 : yMax * 0.02

  // Recent high reference line
  const recentSlice = sliced.slice(-recentHighDays)
  const recentHigh = recentSlice.length > 0 ? Math.max(...recentSlice.map((d) => d.close)) : null

  const shapes: Partial<Plotly.Shape>[] = recentHigh
    ? [
        {
          type: "line" as const,
          x0: dates[0],
          x1: dates[dates.length - 1],
          y0: recentHigh,
          y1: recentHigh,
          line: { color: "#FFA500", width: 1, dash: "dash" },
        },
      ]
    : []

  const annotations: Partial<Plotly.Annotations>[] = recentHigh
    ? [
        {
          x: dates[dates.length - 1],
          y: recentHigh,
          xanchor: "right",
          yanchor: "bottom",
          text: t("fx_watch.chart.high_annotation", { days: recentHighDays, high: recentHigh.toFixed(4) }),
          showarrow: false,
          font: { size: 10, color: "#FFA500" },
        },
      ]
    : []

  return (
    <div>
      {/* Period selector */}
      <div className="flex gap-1 mb-1">
        {PERIOD_OPTIONS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            className={`rounded px-2 py-0.5 text-xs border transition-colors ${
              period === p.key
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {p.key}
          </button>
        ))}
      </div>
      <Plot
        data={[
          // Invisible baseline trace at yMin to anchor the fill
          {
            x: [dates[0], dates[dates.length - 1]],
            y: [yMin - padding, yMin - padding],
            type: "scatter",
            mode: "lines",
            line: { color: "transparent", width: 0 },
            showlegend: false,
            hoverinfo: "skip",
          },
          {
            x: dates,
            y: rates,
            type: "scatter",
            mode: "lines",
            line: { color: lineColor, width: 2 },
            fill: "tonexty",
            fillcolor: fillColor,
            hovertemplate: t("fx_watch.chart.hover_template") + "<extra></extra>",
          },
        ]}
        layout={{
          height: 180,
          margin: { l: 40, r: 10, t: 0, b: 30 },
          yaxis: {
            range: [yMin - padding, yMax + padding],
            showgrid: true,
            gridcolor: "rgba(128,128,128,0.1)",
          },
          xaxis: { showgrid: false },
          ...plotlyTheme,
          font: { ...plotlyTheme.font, size: 10 },
          shapes,
          annotations,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  )
}
