import { useState, useCallback, useMemo } from "react"
import { useTranslation } from "react-i18next"
import {
  AreaSeries,
  CrosshairMode,
  LineStyle,
  type IChartApi,
} from "lightweight-charts"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import type { FxHistoryPoint } from "@/api/types/fxWatch"

const PERIOD_OPTIONS = [
  { key: "1M", labelKey: "fx_watch.period.1m", days: 30 },
  { key: "2M", labelKey: "fx_watch.period.2m", days: 60 },
  { key: "3M", labelKey: "fx_watch.period.3m", days: 90 },
]

interface Props {
  data: FxHistoryPoint[]
  recentHighDays: number
}

export function FxChart({ data, recentHighDays }: Props) {
  const { t } = useTranslation()
  const [period, setPeriod] = useState("3M")

  const sliced = useMemo(() => {
    const n = PERIOD_OPTIONS.find((p) => p.key === period)?.days ?? 90
    return data.length >= n ? data.slice(-n) : data
  }, [data, period])

  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { mode: CrosshairMode.Normal },
        grid: { vertLines: { visible: false } },
        timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
        rightPriceScale: { borderVisible: false },
      })

      const rates = sliced.map((d) => d.close)
      const isUp = rates.length >= 2 && rates[rates.length - 1] >= rates[0]

      const series = chart.addSeries(AreaSeries, {
        lineColor: isUp ? "#00c805" : "#ff5252",
        topColor: isUp ? "rgba(0,200,5,0.2)" : "rgba(255,82,82,0.2)",
        bottomColor: "rgba(0,0,0,0)",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
      })

      series.setData(
        sliced.map((d) => ({
          time: d.date as `${number}-${number}-${number}`,
          value: d.close,
        })),
      )

      // Recent high reference line via createPriceLine
      const recentSlice = sliced.slice(-recentHighDays)
      if (recentSlice.length > 0) {
        const recentHigh = Math.max(...recentSlice.map((d) => d.close))
        series.createPriceLine({
          price: recentHigh,
          color: "#FFA500",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: t("fx_watch.chart.high_annotation", { days: recentHighDays, high: recentHigh.toFixed(4) }),
          lineVisible: true,
          axisLabelColor: "#FFA500",
          axisLabelTextColor: "#fff",
        })
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sliced, recentHighDays],
  )

  if (!data || data.length < 5) {
    return <p className="text-xs text-muted-foreground">{t("fx_watch.chart.insufficient_data")}</p>
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
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(p.labelKey)}
          </button>
        ))}
      </div>
      <LightweightChartWrapper key={period} height={180} onInit={onInit} />
    </div>
  )
}
