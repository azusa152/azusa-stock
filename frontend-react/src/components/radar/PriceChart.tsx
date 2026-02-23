import { useState, useMemo, useCallback } from "react"
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

// Approximate trading days per calendar period
const PERIOD_OPTIONS = [
  { key: "1M", labelKey: "radar.stock_card.period.1m", days: 22 },
  { key: "3M", labelKey: "radar.stock_card.period.3m", days: 66 },
  { key: "6M", labelKey: "radar.stock_card.period.6m", days: 132 },
  { key: "1Y", labelKey: "radar.stock_card.period.1y", days: Infinity },
] as const

function calcMA(closes: number[], period: number): (number | null)[] {
  return closes.map((_, i) => {
    if (i < period - 1) return null
    const slice = closes.slice(i - period + 1, i + 1)
    return slice.reduce((a, b) => a + b, 0) / period
  })
}

export function PriceChart({ data }: Props) {
  const { t } = useTranslation()
  const [period, setPeriod] = useState("3M")

  // Slice visible data client-side; MA is computed on full dataset first, then sliced together
  const { sliced, slicedMA200, slicedMA60 } = useMemo(() => {
    const closes = data.map((d) => d.close)
    const ma200 = calcMA(closes, 200)
    const ma60 = calcMA(closes, 60)

    const n = PERIOD_OPTIONS.find((p) => p.key === period)?.days ?? Infinity
    const start = n === Infinity ? 0 : Math.max(0, data.length - n)

    return {
      sliced: data.slice(start),
      slicedMA200: ma200.slice(start),
      slicedMA60: ma60.slice(start),
    }
  }, [data, period])

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
        sliced.map((d) => ({ time: d.date as `${number}-${number}-${number}`, value: d.close })),
      )

      ma200Series.setData(
        sliced
          .map((d, i) => ({ time: d.date as `${number}-${number}-${number}`, value: slicedMA200[i] }))
          .filter((p): p is { time: `${number}-${number}-${number}`; value: number } => p.value != null),
      )

      ma60Series.setData(
        sliced
          .map((d, i) => ({ time: d.date as `${number}-${number}-${number}`, value: slicedMA60[i] }))
          .filter((p): p is { time: `${number}-${number}-${number}`; value: number } => p.value != null),
      )
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sliced, slicedMA200, slicedMA60],
  )

  if (!data || data.length < 5) {
    return <p className="text-xs text-muted-foreground">{t("chart.insufficient_data")}</p>
  }

  return (
    <div>
      <div className="flex gap-1 mb-1">
        {PERIOD_OPTIONS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            className={`rounded px-2 py-0.5 text-xs border transition-colors ${
              period === p.key
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:text-foreground hover:border-foreground"
            }`}
          >
            {t(p.labelKey)}
          </button>
        ))}
      </div>
      <LightweightChartWrapper key={period} height={200} onInit={onInit} />
    </div>
  )
}
