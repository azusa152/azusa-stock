import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import Plot from "react-plotly.js"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  CATEGORY_ICON_SHORT,
  CATEGORY_COLOR_MAP,
  CATEGORY_COLOR_FALLBACK,
} from "@/lib/constants"
import type { RebalanceResponse, ProfileResponse } from "@/api/types/dashboard"

interface Props {
  rebalance?: RebalanceResponse | null
  profile?: ProfileResponse | null
}

export function AllocationGlance({ rebalance, profile }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  if (!rebalance || !profile || !rebalance.categories) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">{t("dashboard.no_allocation_data")}</p>
          <div className="flex gap-2 mt-3">
            <Button size="sm" variant="outline" onClick={() => navigate("/allocation")}>
              {t("dashboard.button_setup_persona")}
            </Button>
            <Button size="sm" variant="outline" onClick={() => navigate("/radar")}>
              {t("dashboard.button_track_stock")}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const targetConfig = profile.config
  const breakdown = rebalance.categories

  const catKeys = Object.keys(targetConfig)
  const catLabels = catKeys.map((k) => {
    const icon = CATEGORY_ICON_SHORT[k] ?? ""
    return `${icon} ${k}`
  })
  const targetVals = catKeys.map((k) => targetConfig[k] ?? 0)
  const actualVals = catKeys.map((k) => breakdown[k]?.current_pct ?? 0)
  const colors = catKeys.map((k) => CATEGORY_COLOR_MAP[k] ?? CATEGORY_COLOR_FALLBACK)

  const driftLabels = catKeys.map((k) => `${CATEGORY_ICON_SHORT[k] ?? ""} ${k}`)
  const driftVals = catKeys.map((k) => breakdown[k]?.drift_pct ?? 0)
  const driftColors = driftVals.map((d) => (Math.abs(d) > 5 ? "#ef4444" : "#9CA3AF"))

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("dashboard.allocation_title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dual donut */}
        <Plot
          data={[
            {
              type: "pie",
              labels: catLabels,
              values: targetVals,
              hole: 0.4,
              marker: { colors },
              textinfo: "percent",
              domain: { column: 0 },
              hovertemplate: "<b>%{label}</b><br>" + t("dashboard.chart.target_pct") + ": %{percent}<extra></extra>",
              name: t("dashboard.chart.target"),
            },
            {
              type: "pie",
              labels: catLabels,
              values: actualVals,
              hole: 0.4,
              marker: { colors },
              textinfo: "percent",
              domain: { column: 1 },
              hovertemplate: "<b>%{label}</b><br>" + t("dashboard.chart.actual_pct") + ": %{percent}<extra></extra>",
              name: t("dashboard.chart.actual"),
            },
          ]}
          layout={{
            height: 260,
            margin: { l: 20, r: 20, t: 40, b: 20 },
            showlegend: false,
            grid: { rows: 1, columns: 2 },
            annotations: [
              { text: t("dashboard.chart.target"), x: 0.18, y: 1.08, xref: "paper", yref: "paper", showarrow: false, font: { size: 12 } },
              { text: t("dashboard.chart.actual"), x: 0.82, y: 1.08, xref: "paper", yref: "paper", showarrow: false, font: { size: 12 } },
            ],
            plot_bgcolor: "rgba(0,0,0,0)",
            paper_bgcolor: "rgba(0,0,0,0)",
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />

        {/* Drift bar */}
        <Plot
          data={[
            {
              type: "bar",
              x: driftLabels,
              y: driftVals,
              marker: { color: driftColors },
              text: driftVals.map((d) => `${d >= 0 ? "+" : ""}${d.toFixed(1)}%`),
              textposition: "outside",
            },
          ]}
          layout={{
            height: 260,
            margin: { l: 30, r: 10, t: 40, b: 30 },
            title: { text: t("dashboard.drift_title"), font: { size: 13 }, x: 0.5, xanchor: "center" } as Partial<Plotly.Layout["title"]>,
            yaxis: { title: { text: t("dashboard.chart.drift_yaxis") } },
            showlegend: false,
            shapes: [
              { type: "line", x0: -0.5, x1: catKeys.length - 0.5, y0: 5, y1: 5, line: { color: "orange", dash: "dash", width: 1 } },
              { type: "line", x0: -0.5, x1: catKeys.length - 0.5, y0: -5, y1: -5, line: { color: "orange", dash: "dash", width: 1 } },
            ],
            annotations: [
              { x: catKeys.length - 0.5, y: 5, text: "+5%", xref: "x", yref: "y", showarrow: false, font: { size: 10, color: "orange" } },
              { x: catKeys.length - 0.5, y: -5, text: "-5%", xref: "x", yref: "y", showarrow: false, font: { size: 10, color: "orange" } },
            ],
            plot_bgcolor: "rgba(0,0,0,0)",
            paper_bgcolor: "rgba(0,0,0,0)",
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </CardContent>
    </Card>
  )
}
