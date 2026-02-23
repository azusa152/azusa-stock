import { useCallback } from "react"
import { AreaSeries, type IChartApi } from "lightweight-charts"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import type { PricePoint } from "@/api/hooks/useRadar"

interface Props {
  data: PricePoint[]
}

/** Tiny 40px area sparkline for stock card collapsed headers. No axes, no grid, no crosshair. */
export function SparklineHeader({ data }: Props) {
  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { vertLine: { visible: false }, horzLine: { visible: false } },
        grid: { vertLines: { visible: false }, horzLines: { visible: false } },
        timeScale: { visible: false },
        rightPriceScale: { visible: false },
        leftPriceScale: { visible: false },
        handleScroll: false,
        handleScale: false,
      })

      const last = data[data.length - 1]?.close ?? 0
      const first = data[0]?.close ?? 0
      const isUp = last >= first
      const lineColor = isUp ? "#22c55e" : "#ef4444"
      const topColor = isUp ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"

      const series = chart.addSeries(AreaSeries, {
        lineColor,
        topColor,
        bottomColor: "rgba(0,0,0,0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })

      series.setData(
        data.map((d) => ({
          time: d.date as `${number}-${number}-${number}`,
          value: d.close,
        })),
      )
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  )

  if (data.length < 5) return null

  return (
    <div className="w-16 shrink-0">
      <LightweightChartWrapper height={40} onInit={onInit} />
    </div>
  )
}
