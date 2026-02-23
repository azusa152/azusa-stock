import { useState } from "react"
import { useTranslation } from "react-i18next"
import { LazyPlot as Plot } from "@/components/LazyPlot"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Snapshot } from "@/api/types/dashboard"
import { usePlotlyTheme } from "@/hooks/usePlotlyTheme"

const PERIOD_OPTIONS: { key: string; labelKey: string; days: number | "YTD" | "ALL" }[] = [
  { key: "1W", labelKey: "dashboard.performance_period_1w", days: 7 },
  { key: "1M", labelKey: "dashboard.performance_period_1m", days: 30 },
  { key: "3M", labelKey: "dashboard.performance_period_3m", days: 90 },
  { key: "6M", labelKey: "dashboard.performance_period_6m", days: 180 },
  { key: "YTD", labelKey: "dashboard.performance_period_ytd", days: "YTD" },
  { key: "1Y", labelKey: "dashboard.performance_period_1y", days: 365 },
  { key: "ALL", labelKey: "dashboard.performance_period_all", days: "ALL" },
]

interface Props {
  snapshots: Snapshot[]
}

export function PerformanceChart({ snapshots }: Props) {
  const { t } = useTranslation()
  const plotlyTheme = usePlotlyTheme()
  const [selectedKey, setSelectedKey] = useState("1M")

  const today = new Date()

  function getCutoff(key: string): string {
    const opt = PERIOD_OPTIONS.find((p) => p.key === key)!
    if (opt.days === "ALL") return ""
    if (opt.days === "YTD") {
      return `${today.getFullYear()}-01-01`
    }
    const d = new Date(today)
    d.setDate(d.getDate() - (opt.days as number))
    return d.toISOString().slice(0, 10)
  }

  const cutoff = getCutoff(selectedKey)
  const filtered = cutoff ? snapshots.filter((s) => s.snapshot_date >= cutoff) : snapshots

  let plotData: Plotly.Data[] = []
  if (filtered.length >= 2) {
    const dates = filtered.map((s) => s.snapshot_date)
    const values = filtered.map((s) => s.total_value)
    const baseVal = values[0] || 1
    const pctReturns = values.map((v) => (v / baseVal - 1) * 100)

    const isUp = pctReturns[pctReturns.length - 1] >= 0
    const lineColor = isUp ? "#22c55e" : "#ef4444"
    const fillColor = isUp ? "rgba(34,197,94,0.07)" : "rgba(239,68,68,0.07)"

    plotData = [
      {
        x: dates,
        y: pctReturns,
        type: "scatter",
        mode: "lines",
        line: { color: lineColor, width: 2 },
        fill: "tozeroy",
        fillcolor: fillColor,
        customdata: values,
        hovertemplate: "%{x}<br>%{y:+.2f}%  ($%{customdata:,.0f})<extra></extra>",
        name: t("dashboard.total_market_value"),
      },
    ]

    const benchmarkPairs = filtered
      .map((s, i) => ({ d: dates[i], b: s.benchmark_value }))
      .filter((p): p is { d: string; b: number } => p.b != null)

    if (benchmarkPairs.length >= 2) {
      const baseB = benchmarkPairs[0].b || 1
      plotData.push({
        x: benchmarkPairs.map((p) => p.d),
        y: benchmarkPairs.map((p) => (p.b / baseB - 1) * 100),
        type: "scatter",
        mode: "lines",
        line: { color: "#888", width: 1, dash: "dot" },
        name: t("dashboard.performance_benchmark_label"),
        hovertemplate: "%{x}<br>S&P500 %{y:+.2f}%<extra></extra>",
      })
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("dashboard.performance_title")}</CardTitle>
        <div className="flex flex-wrap gap-1 mt-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setSelectedKey(opt.key)}
              className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                selectedKey === opt.key
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border hover:bg-accent"
              }`}
            >
              {t(opt.labelKey)}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {filtered.length >= 2 ? (
          <Plot
            data={plotData}
            layout={{
              height: 280,
              margin: { l: 40, r: 10, t: 10, b: 30 },
              yaxis: {
                showgrid: true,
                gridcolor: "rgba(128,128,128,0.15)",
                ticksuffix: "%",
                zeroline: true,
                zerolinecolor: "rgba(128,128,128,0.3)",
              },
              xaxis: { showgrid: false },
              showlegend: plotData.length > 1,
              legend: { orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "right", x: 1 },
              hovermode: "x unified",
              ...plotlyTheme,
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />
        ) : (
          <p className="text-sm text-muted-foreground py-4">
            {t("dashboard.performance_no_data")}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
