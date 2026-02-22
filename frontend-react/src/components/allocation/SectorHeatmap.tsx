import { useTranslation } from "react-i18next"
import Plot from "react-plotly.js"
import type { SectorExposureItem } from "@/api/types/allocation"

interface Props {
  data: SectorExposureItem[]
}

export function SectorHeatmap({ data }: Props) {
  const { t } = useTranslation()

  if (!data || data.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.sector.title")}</p>
        <p className="text-sm text-muted-foreground">{t("allocation.sector.empty")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.sector.title")}</p>
      <Plot
        data={[
          {
            type: "treemap",
            labels: data.map((d) => d.sector),
            values: data.map((d) => d.value),
            parents: data.map(() => ""),
            hovertemplate: "%{label}<br>%{customdata:.1f}%<extra></extra>",
            customdata: data.map((d) => d.weight_pct),
            textinfo: "label",
          },
        ]}
        layout={{
          height: 250,
          margin: { l: 0, r: 0, t: 5, b: 0 },
          plot_bgcolor: "rgba(0,0,0,0)",
          paper_bgcolor: "rgba(0,0,0,0)",
          font: { size: 11 },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
        useResizeHandler
      />
    </div>
  )
}
