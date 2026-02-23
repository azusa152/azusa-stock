import { useCallback } from "react"
import { useTranslation } from "react-i18next"
import {
  AreaSeries,
  LineSeries,
  LineStyle,
  CrosshairMode,
  type IChartApi,
} from "lightweight-charts"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
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

  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { mode: CrosshairMode.Normal },
        grid: { vertLines: { visible: false } },
        timeScale: {
          borderVisible: false,
          fixLeftEdge: true,
          fixRightEdge: true,
        },
        rightPriceScale: { borderVisible: false },
      })

      const closes = data.map((d) => d.close)
      const ma200 = calcMA(closes, 200)
      const ma60 = calcMA(closes, 60)

      const areaSeries = chart.addSeries(AreaSeries, {
        lineColor: "#4f8ef7",
        topColor: "rgba(79,142,247,0.35)",
        bottomColor: "rgba(79,142,247,0.02)",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
      })

      const ma200Series = chart.addSeries(LineSeries, {
        color: "#f97316",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        title: t("chart.ma200"),
      })

      const ma60Series = chart.addSeries(LineSeries, {
        color: "#a78bfa",
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        title: t("chart.ma60"),
      })

      areaSeries.setData(
        data.map((d) => ({ time: d.date as `${number}-${number}-${number}`, value: d.close })),
      )

      ma200Series.setData(
        data
          .map((d, i) => ({ time: d.date as `${number}-${number}-${number}`, value: ma200[i] }))
          .filter((p): p is { time: `${number}-${number}-${number}`; value: number } => p.value != null),
      )

      ma60Series.setData(
        data
          .map((d, i) => ({ time: d.date as `${number}-${number}-${number}`, value: ma60[i] }))
          .filter((p): p is { time: `${number}-${number}-${number}`; value: number } => p.value != null),
      )
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  )

  if (!data || data.length < 5) {
    return <p className="text-xs text-muted-foreground">{t("chart.insufficient_data")}</p>
  }

  return <LightweightChartWrapper height={200} onInit={onInit} />
}
