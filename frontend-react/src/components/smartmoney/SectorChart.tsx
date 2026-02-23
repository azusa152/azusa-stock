import { useTranslation } from "react-i18next"
import { LazyPlot as Plot } from "@/components/LazyPlot"
import type { SectorBreakdownItem } from "@/api/types/smartMoney"
import { usePlotlyTheme } from "@/hooks/usePlotlyTheme"

interface Props {
  data: SectorBreakdownItem[]
}

export function SectorChart({ data }: Props) {
  const { t } = useTranslation()
  const plotlyTheme = usePlotlyTheme()

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t("smart_money.overview.sector_empty")}</p>
    )
  }

  const sorted = [...data].sort((a, b) => b.weight_pct - a.weight_pct)
  const sectors = sorted.map((d) => d.sector)
  const weights = sorted.map((d) => d.weight_pct)

  return (
    <Plot
      data={[
        {
          type: "bar",
          orientation: "h",
          x: weights,
          y: sectors,
          marker: { color: "#3b82f6" },
          hovertemplate: "%{y}: %{x:.1f}%<extra></extra>",
        },
      ]}
      layout={{
        height: Math.max(180, sorted.length * 28 + 60),
        margin: { l: 120, r: 20, t: 10, b: 30 },
        xaxis: {
          title: { text: t("smart_money.overview.sector_weight_axis") },
          showgrid: true,
          gridcolor: "rgba(128,128,128,0.1)",
        },
        yaxis: { showgrid: false, automargin: true },
        ...plotlyTheme,
        font: { ...plotlyTheme.font, size: 11 },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  )
}
