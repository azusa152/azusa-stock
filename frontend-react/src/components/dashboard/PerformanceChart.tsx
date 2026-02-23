import { useState, useCallback, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { AreaSeries, LineSeries, LineStyle, CrosshairMode, type IChartApi } from "lightweight-charts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import type { Snapshot } from "@/api/types/dashboard"

const PERIOD_OPTIONS: { key: string; labelKey: string; days: number | "YTD" | "ALL" }[] = [
  { key: "1W", labelKey: "dashboard.performance_period_1w", days: 7 },
  { key: "1M", labelKey: "dashboard.performance_period_1m", days: 30 },
  { key: "3M", labelKey: "dashboard.performance_period_3m", days: 90 },
  { key: "6M", labelKey: "dashboard.performance_period_6m", days: 180 },
  { key: "YTD", labelKey: "dashboard.performance_period_ytd", days: "YTD" },
  { key: "1Y", labelKey: "dashboard.performance_period_1y", days: 365 },
  { key: "ALL", labelKey: "dashboard.performance_period_all", days: "ALL" },
]

interface Props {
  snapshots: Snapshot[]
}

export function PerformanceChart({ snapshots }: Props) {
  const { t } = useTranslation()
  const [selectedKey, setSelectedKey] = useState("1M")

  const filtered = useMemo(() => {
    const opt = PERIOD_OPTIONS.find((p) => p.key === selectedKey)!
    if (opt.days === "ALL") return snapshots
    const now = new Date()
    const cutoff =
      opt.days === "YTD"
        ? `${now.getFullYear()}-01-01`
        : (() => {
            const d = new Date(now)
            d.setDate(d.getDate() - (opt.days as number))
            return d.toISOString().slice(0, 10)
          })()
    return snapshots.filter((s) => s.snapshot_date >= cutoff)
  }, [snapshots, selectedKey])

  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { mode: CrosshairMode.Normal },
        grid: { vertLines: { visible: false } },
        timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
        rightPriceScale: { borderVisible: false },
      })

      if (filtered.length < 2) return

      const values = filtered.map((s) => s.total_value)
      const baseVal = values[0] || 1
      const pctReturns = values.map((v) => (v / baseVal - 1) * 100)
      const isUp = pctReturns[pctReturns.length - 1] >= 0

      const areaSeries = chart.addSeries(AreaSeries, {
        lineColor: isUp ? "#22c55e" : "#ef4444",
        topColor: isUp ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)",
        bottomColor: "rgba(0,0,0,0)",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        priceFormat: { type: "percent", precision: 2, minMove: 0.01 },
        title: t("dashboard.total_market_value"),
      })

      areaSeries.setData(
        filtered.map((s, i) => ({
          time: s.snapshot_date as `${number}-${number}-${number}`,
          value: pctReturns[i],
        })),
      )

      // Benchmark
      const benchmarkPairs = filtered
        .map((s) => ({ d: s.snapshot_date, b: s.benchmark_value }))
        .filter((p): p is { d: string; b: number } => p.b != null)

      if (benchmarkPairs.length >= 2) {
        const baseB = benchmarkPairs[0].b || 1
        const benchmarkSeries = chart.addSeries(LineSeries, {
          color: "#9ca3af",
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          priceLineVisible: false,
          lastValueVisible: false,
          priceFormat: { type: "percent", precision: 2, minMove: 0.01 },
          title: t("dashboard.performance_benchmark_label"),
        })
        benchmarkSeries.setData(
          benchmarkPairs.map((p) => ({
            time: p.d as `${number}-${number}-${number}`,
            value: (p.b / baseB - 1) * 100,
          })),
        )
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filtered],
  )

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("dashboard.performance_title")}</CardTitle>
        <div className="flex flex-wrap gap-1 mt-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setSelectedKey(opt.key)}
              className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                selectedKey === opt.key
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border hover:bg-accent"
              }`}
            >
              {t(opt.labelKey)}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {filtered.length >= 2 ? (
          <LightweightChartWrapper key={selectedKey} height={280} onInit={onInit} />
        ) : (
          <p className="text-sm text-muted-foreground py-4">{t("dashboard.performance_no_data")}</p>
        )}
      </CardContent>
    </Card>
  )
}
