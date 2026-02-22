import { useTranslation } from "react-i18next"
import Plot from "react-plotly.js"
import type { CategoryAllocation } from "@/api/types/allocation"

interface Props {
  categories: Record<string, CategoryAllocation>
}

export function DriftChart({ categories }: Props) {
  const { t } = useTranslation()

  const entries = Object.entries(categories).sort((a, b) => b[1].drift_pct - a[1].drift_pct)
  const labels = entries.map(([name]) => name)
  const drifts = entries.map(([, v]) => v.drift_pct)
  const barColors = drifts.map((d) => (d > 0 ? "#ef4444" : "#22c55e"))

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.drift.title")}</p>
      <Plot
        data={[
          {
            type: "bar",
            orientation: "h",
            x: drifts,
            y: labels,
            marker: { color: barColors },
            hovertemplate: "%{y}: %{x:.1f}%<extra></extra>",
          },
        ]}
        layout={{
          height: Math.max(160, entries.length * 32 + 60),
          margin: { l: 100, r: 20, t: 10, b: 40 },
          xaxis: {
            title: { text: t("allocation.drift.axis_label") },
            showgrid: true,
            gridcolor: "rgba(128,128,128,0.1)",
            zeroline: true,
          },
          yaxis: { showgrid: false },
          shapes: [
            // ±5% yellow bands
            {
              type: "line", x0: 5, x1: 5, y0: -0.5, y1: entries.length - 0.5,
              line: { color: "#f59e0b", width: 1, dash: "dot" },
            },
            {
              type: "line", x0: -5, x1: -5, y0: -0.5, y1: entries.length - 0.5,
              line: { color: "#f59e0b", width: 1, dash: "dot" },
            },
            // ±10% orange bands
            {
              type: "line", x0: 10, x1: 10, y0: -0.5, y1: entries.length - 0.5,
              line: { color: "#f97316", width: 1, dash: "dash" },
            },
            {
              type: "line", x0: -10, x1: -10, y0: -0.5, y1: entries.length - 0.5,
              line: { color: "#f97316", width: 1, dash: "dash" },
            },
          ],
          plot_bgcolor: "rgba(0,0,0,0)",
          paper_bgcolor: "rgba(0,0,0,0)",
          font: { size: 10 },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span>
          <span className="inline-block w-3 h-px bg-yellow-500 mr-1 align-middle" />
          {t("allocation.drift.threshold_5")}
        </span>
        <span>
          <span className="inline-block w-3 h-px bg-orange-500 mr-1 align-middle" />
          {t("allocation.drift.threshold_10")}
        </span>
      </div>
    </div>
  )
}
