import { useState } from "react"
import { useTranslation } from "react-i18next"
import Plot from "react-plotly.js"
import type { CategoryAllocation } from "@/api/types/allocation"
import { CATEGORY_COLOR_MAP, CATEGORY_COLOR_FALLBACK } from "@/lib/constants"

interface Props {
  categories: Record<string, CategoryAllocation>
}

function getCategoryColor(name: string): string {
  return CATEGORY_COLOR_MAP[name] ?? CATEGORY_COLOR_FALLBACK
}

export function AllocationCharts({ categories }: Props) {
  const { t } = useTranslation()
  const [chartType, setChartType] = useState<"pie" | "treemap">("pie")

  const entries = Object.entries(categories)
  const labels = entries.map(([name]) => name)
  const targetValues = entries.map(([, v]) => v.target_pct)
  const actualValues = entries.map(([, v]) => v.current_pct)
  const colors = labels.map(getCategoryColor)

  const commonLayout = {
    height: 260,
    margin: { l: 0, r: 0, t: 30, b: 0 },
    plot_bgcolor: "rgba(0,0,0,0)",
    paper_bgcolor: "rgba(0,0,0,0)",
    font: { size: 11 },
    showlegend: true,
    legend: { orientation: "h" as const, y: -0.1 },
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{t("allocation.charts.title")}</p>
        <div className="flex gap-1">
          <button
            onClick={() => setChartType("pie")}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${
              chartType === "pie" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-muted/30"
            }`}
          >
            {t("allocation.charts.toggle_pie")}
          </button>
          <button
            onClick={() => setChartType("treemap")}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${
              chartType === "treemap" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-muted/30"
            }`}
          >
            {t("allocation.charts.toggle_treemap")}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {/* Target */}
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.charts.target")}</p>
          {chartType === "pie" ? (
            <Plot
              data={[{
                type: "pie",
                labels,
                values: targetValues,
                marker: { colors },
                hole: 0.3,
                hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
                textinfo: "label+percent",
              }]}
              layout={{ ...commonLayout, showlegend: false }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          ) : (
            <Plot
              data={[{
                type: "treemap",
                labels,
                values: targetValues,
                parents: labels.map(() => ""),
                marker: { colors },
                hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
              }]}
              layout={{ ...commonLayout, showlegend: false }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          )}
        </div>

        {/* Actual */}
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.charts.actual")}</p>
          {chartType === "pie" ? (
            <Plot
              data={[{
                type: "pie",
                labels,
                values: actualValues,
                marker: { colors },
                hole: 0.3,
                hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
                textinfo: "label+percent",
              }]}
              layout={{ ...commonLayout, showlegend: false }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          ) : (
            <Plot
              data={[{
                type: "treemap",
                labels,
                values: actualValues,
                parents: labels.map(() => ""),
                marker: { colors },
                hovertemplate: "%{label}: %{value:.1f}%<extra></extra>",
              }]}
              layout={{ ...commonLayout, showlegend: false }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
              useResizeHandler
            />
          )}
        </div>
      </div>
    </div>
  )
}
