import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { LazyPlot as Plot } from "@/components/LazyPlot"
import { usePlotlyTheme } from "@/hooks/usePlotlyTheme"
import type { PricePoint } from "@/api/hooks/useRadar"

interface Props {
  data: PricePoint[]
}

function calcMA(closes: number[], period: number): (number | null)[] {
  return closes.map((_, i) => {
    if (i < period - 1) return null
    const slice = closes.slice(i - period + 1, i + 1)
    return slice.reduce((a, b) => a + b, 0) / period
  })
}

export function PriceChart({ data }: Props) {
  const { t } = useTranslation()
  const plotlyTheme = usePlotlyTheme()

  if (!data || data.length < 5) {
    return <p className="text-xs text-muted-foreground">{t("chart.insufficient_data")}</p>
  }

  const { dates, closes, ma200, ma60 } = useMemo(() => {
    const dates = data.map((d) => d.date)
    const closes = data.map((d) => d.close)
    return {
      dates,
      closes,
      ma200: calcMA(closes, 200),
      ma60: calcMA(closes, 60),
    }
  }, [data])

  const traces: Plotly.Data[] = [
    {
      x: dates,
      y: closes,
      type: "scatter",
      mode: "lines",
      name: t("chart.close_price"),
      line: { color: "#4f8ef7", width: 1.5 },
      hovertemplate: "%{x}<br>$%{y:.2f}<extra></extra>",
    },
    {
      x: dates,
      y: ma200,
      type: "scatter",
      mode: "lines",
      name: t("chart.ma200"),
      line: { color: "#f97316", width: 1, dash: "dash" },
      hovertemplate: `${t("chart.ma200")}: $%{y:.2f}<extra></extra>`,
      connectgaps: false,
    },
    {
      x: dates,
      y: ma60,
      type: "scatter",
      mode: "lines",
      name: t("chart.ma60"),
      line: { color: "#a78bfa", width: 1, dash: "dot" },
      hovertemplate: `${t("chart.ma60")}: $%{y:.2f}<extra></extra>`,
      connectgaps: false,
    },
  ]

  return (
    <Plot
      data={traces}
      layout={{
        height: 200,
        margin: { l: 45, r: 10, t: 4, b: 28 },
        legend: {
          orientation: "h",
          x: 0,
          y: 1.12,
          font: { size: 10 },
        },
        xaxis: { showgrid: false, tickfont: { size: 9 } },
        yaxis: {
          showgrid: true,
          gridcolor: "rgba(128,128,128,0.1)",
          tickfont: { size: 9 },
          tickprefix: "$",
        },
        ...plotlyTheme,
        font: { ...plotlyTheme.font, size: 10 },
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  )
}
