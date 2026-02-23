import { useEffect, useRef, useCallback } from "react"
import { createChart, type IChartApi, type DeepPartial, type ChartOptions } from "lightweight-charts"
import { useLightweightChartTheme } from "@/hooks/useLightweightChartTheme"

interface Props {
  height?: number
  /** Called once with the chart instance on mount; return cleanup if needed. */
  onInit: (chart: IChartApi, container: HTMLDivElement) => (() => void) | void
  className?: string
}

/**
 * Reusable wrapper for lightweight-charts.
 * Handles: chart creation, ResizeObserver, theme reactivity, and cleanup.
 */
export function LightweightChartWrapper({ height = 200, onInit, className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesCleanupRef = useRef<(() => void) | void>(undefined)
  const theme = useLightweightChartTheme()

  // Keep a stable ref to the latest onInit to avoid re-running the chart setup
  const onInitRef = useRef(onInit)
  onInitRef.current = onInit

  // Re-apply theme when it changes without recreating the chart
  const themeRef = useRef(theme)
  themeRef.current = theme

  const applyTheme = useCallback((chart: IChartApi) => {
    const t = themeRef.current
    const opts: DeepPartial<ChartOptions> = {
      layout: {
        background: t.background,
        textColor: t.textColor,
      },
      grid: {
        vertLines: { color: t.gridColor },
        horzLines: { color: t.gridColor },
      },
    }
    chart.applyOptions(opts)
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      height,
      layout: {
        background: theme.background,
        textColor: theme.textColor,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: theme.gridColor },
        horzLines: { color: theme.gridColor },
      },
      timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
      rightPriceScale: { borderVisible: false },
      handleScroll: false,
      handleScale: false,
    })

    chartRef.current = chart

    // Allow caller to add series, return optional cleanup
    seriesCleanupRef.current = onInitRef.current(chart, container)

    chart.timeScale().fitContent()

    // Responsive resize
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) {
        chart.applyOptions({ width: entry.contentRect.width })
        chart.timeScale().fitContent()
      }
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      if (typeof seriesCleanupRef.current === "function") {
        seriesCleanupRef.current()
      }
      chart.remove()
      chartRef.current = null
    }
    // height is intentionally excluded — changing height doesn't require full remount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Re-apply theme on theme change without rebuilding the chart
  useEffect(() => {
    if (chartRef.current) {
      applyTheme(chartRef.current)
    }
  }, [theme, applyTheme])

  return <div ref={containerRef} style={{ height }} className={className ?? "w-full"} />
}
