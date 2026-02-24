import { useState, useCallback, useEffect, useMemo, useRef } from "react"
import { useTranslation } from "react-i18next"
import {
  AreaSeries,
  LineSeries,
  LineStyle,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
} from "lightweight-charts"
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

interface CrosshairData {
  date: string
  portfolio: number
  benchmark?: number
}

interface Props {
  snapshots: Snapshot[]
}

function formatDate(isoDate: string, locale: string): string {
  // Parse as local date to avoid UTC-offset shift (YYYY-MM-DD → noon UTC)
  const [year, month, day] = isoDate.split("-").map(Number)
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(year, month - 1, day))
}

export function PerformanceChart({ snapshots }: Props) {
  const { t, i18n } = useTranslation()
  const [selectedKey, setSelectedKey] = useState("1M")
  const [crosshair, setCrosshair] = useState<CrosshairData | null>(null)

  // Stable chart / series refs — set once inside onInit, read by the data-update effect
  const chartRef = useRef<IChartApi | null>(null)
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null)
  const benchmarkSeriesRef = useRef<ISeriesApi<"Line"> | null>(null)

  // ── Period filtering ────────────────────────────────────────────────────────
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

  // ── Period return stats ─────────────────────────────────────────────────────
  // Cumulative simple return: (V_last / V_first - 1) × 100
  // Equivalent to TWR for portfolios without interim cash flows — standard
  // approach used by Yahoo Finance, Robinhood, TradingView.
  const periodStats = useMemo(() => {
    if (filtered.length < 2) return null
    const first = filtered[0].total_value
    const last = filtered[filtered.length - 1].total_value
    const returnPct = ((last / (first || 1)) - 1) * 100
    return {
      returnPct,
      from: filtered[0].snapshot_date,
      to: filtered[filtered.length - 1].snapshot_date,
    }
  }, [filtered])

  // ── Chart initialisation — called ONCE on mount via LightweightChartWrapper ─
  // t from react-i18next is guaranteed stable, so this callback is also stable.
  const onInit = useCallback((chart: IChartApi) => {
    chartRef.current = chart

    chart.applyOptions({
      crosshair: { mode: CrosshairMode.Normal },
      grid: { vertLines: { visible: false } },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      rightPriceScale: { borderVisible: false },
    })

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#22c55e",
      topColor: "rgba(34,197,94,0.2)",
      bottomColor: "rgba(0,0,0,0)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      priceFormat: { type: "percent", precision: 2, minMove: 0.01 },
      title: t("dashboard.performance_portfolio_return"),
    })
    areaSeriesRef.current = areaSeries

    const benchmarkSeries = chart.addSeries(LineSeries, {
      color: "#9ca3af",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
      priceFormat: { type: "percent", precision: 2, minMove: 0.01 },
      title: t("dashboard.performance_benchmark_label"),
    })
    benchmarkSeriesRef.current = benchmarkSeries

    // Crosshair subscription: update header metrics on hover instead of
    // floating overlays, matching the UX pattern of Yahoo Finance / Bloomberg.
    const crosshairHandler = (param: MouseEventParams) => {
      const area = areaSeriesRef.current
      if (!param.point || !param.time || !area) {
        setCrosshair(null)
        return
      }
      const areaData = param.seriesData.get(area) as { value: number } | undefined
      if (!areaData) {
        setCrosshair(null)
        return
      }
      const bench = benchmarkSeriesRef.current
      const benchData = bench
        ? (param.seriesData.get(bench) as { value: number } | undefined)
        : undefined
      setCrosshair({
        date: typeof param.time === "string" ? param.time : String(param.time),
        portfolio: areaData.value,
        benchmark: benchData?.value,
      })
    }
    chart.subscribeCrosshairMove(crosshairHandler)
    return () => chart.unsubscribeCrosshairMove(crosshairHandler)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // t is stable per react-i18next contract; onInit only runs once on mount

  // ── In-place data update when period changes ────────────────────────────────
  useEffect(() => {
    const chart = chartRef.current
    const areaSeries = areaSeriesRef.current
    const benchmarkSeries = benchmarkSeriesRef.current
    if (!chart || !areaSeries || !benchmarkSeries) return

    setCrosshair(null)

    if (filtered.length < 2) {
      areaSeries.setData([])
      benchmarkSeries.setData([])
      return
    }

    const values = filtered.map((s) => s.total_value)
    const baseVal = values[0] || 1
    const pctReturns = values.map((v) => (v / baseVal - 1) * 100)
    const isUp = pctReturns[pctReturns.length - 1] >= 0

    // Dynamically update line / fill color based on period return
    areaSeries.applyOptions({
      lineColor: isUp ? "#22c55e" : "#ef4444",
      topColor: isUp ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)",
    })

    areaSeries.setData(
      filtered.map((s, i) => ({
        time: s.snapshot_date as `${number}-${number}-${number}`,
        value: pctReturns[i],
      })),
    )

    // Benchmark: both portfolio and S&P 500 rebased to 0% at period start
    // (standard "indexed comparison" / "growth of $1" approach)
    const benchmarkPairs = filtered
      .map((s) => ({ d: s.snapshot_date, b: s.benchmark_value }))
      .filter((p): p is { d: string; b: number } => p.b != null)

    if (benchmarkPairs.length >= 2) {
      const baseB = benchmarkPairs[0].b || 1
      benchmarkSeries.setData(
        benchmarkPairs.map((p) => ({
          time: p.d as `${number}-${number}-${number}`,
          value: (p.b / baseB - 1) * 100,
        })),
      )
    } else {
      benchmarkSeries.setData([])
    }

    chart.timeScale().fitContent()
  }, [filtered])

  const hasSnapshots = snapshots.length >= 2
  const hasPeriodData = filtered.length >= 2

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <Card>
      <CardHeader className="pb-2">
        {/* Title row — shows period return % when idle, crosshair values on hover */}
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{t("dashboard.performance_title")}</CardTitle>
          {crosshair ? (
            <span
              className={`text-xs font-mono tabular-nums ${
                crosshair.portfolio >= 0 ? "text-green-500" : "text-red-500"
              }`}
            >
              {crosshair.portfolio >= 0 ? "+" : ""}
              {crosshair.portfolio.toFixed(2)}%
              {crosshair.benchmark !== undefined && (
                <span className="text-muted-foreground">
                  {" "}/ {t("dashboard.performance_benchmark_label")}:{" "}
                  {crosshair.benchmark >= 0 ? "+" : ""}
                  {crosshair.benchmark.toFixed(2)}%
                </span>
              )}
            </span>
          ) : (
            periodStats && (
              <span
                className={`text-sm font-bold tabular-nums ${
                  periodStats.returnPct >= 0 ? "text-green-500" : "text-red-500"
                }`}
              >
                {periodStats.returnPct >= 0 ? "+" : ""}
                {periodStats.returnPct.toFixed(2)}%
              </span>
            )
          )}
        </div>

        {/* Period selector */}
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

        {/* Sub-caption: date range when idle, hovered date when crosshair active */}
        <p className="text-xs text-muted-foreground mt-0.5 h-4">
          {crosshair
            ? formatDate(crosshair.date, i18n.language)
            : periodStats
              ? `${formatDate(periodStats.from, i18n.language)} → ${formatDate(periodStats.to, i18n.language)}`
              : ""}
        </p>
      </CardHeader>

      <CardContent>
        {hasSnapshots ? (
          <div className="relative">
            {/* Chart is mounted once — never remounted on period change */}
            <LightweightChartWrapper height={280} onInit={onInit} />
            {/* Overlay when selected period has no data yet */}
            {!hasPeriodData && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/70 rounded">
                <p className="text-sm text-muted-foreground">
                  {t("dashboard.performance_no_period_data")}
                </p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-4">
            {t("dashboard.performance_no_data")}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
