import { useEffect, useMemo, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Download } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  useBackfillStatus,
  useBacktestDetail,
  useBacktestSummary,
} from "@/api/hooks/useBacktest"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { cn, formatLocalTime } from "@/lib/utils"

const WINDOWS = [5, 10, 30, 60]

function signalColor(direction?: string): string {
  return direction === "sell" ? "#ef4444" : "#22c55e"
}

export default function Backtest() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const theme = useRechartsTheme()
  const [sopOpen, setSopOpen] = useState(false)
  const { data: summary, isLoading, isError } = useBacktestSummary()
  const { data: backfillStatus } = useBackfillStatus()
  const selectedSignal = summary?.signals?.[0]?.signal ?? ""
  const [activeSignal, setActiveSignal] = useState("")
  const currentSignal = activeSignal || selectedSignal
  const { data: detail } = useBacktestDetail(currentSignal, 50, !!currentSignal)
  const wasBackfillingRef = useRef(false)
  const isBackfilling = backfillStatus?.is_backfilling ?? false
  const totalStocks = backfillStatus?.total ?? 0
  const completedStocks = backfillStatus?.completed ?? 0
  const progressPct =
    totalStocks > 0 ? Math.min((completedStocks / totalStocks) * 100, 100) : 0
  const hasSignals = (summary?.signals?.length ?? 0) > 0
  const showBackfillingState = isBackfilling && !hasSignals
  const showEmptyState = !isBackfilling && !hasSignals

  const handleExportCsv = async () => {
    try {
      const headers: HeadersInit = {}
      const apiKey = import.meta.env.VITE_API_KEY
      if (apiKey) headers["X-API-Key"] = apiKey

      const response = await fetch("/api/backtest/export-csv", { headers })
      if (!response.ok) throw new Error(response.statusText)

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = "backtest_signals.csv"
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(t("common.error"))
    }
  }

  useEffect(() => {
    if (isBackfilling) {
      wasBackfillingRef.current = true
      return
    }
    if (wasBackfillingRef.current) {
      wasBackfillingRef.current = false
      void queryClient.invalidateQueries({ queryKey: ["backtest", "summary"] })
    }
  }, [isBackfilling, queryClient])

  const forwardReturnData = useMemo(() => {
    return (summary?.signals ?? []).map((signal) => {
      const row: Record<string, string | number> = {
        signal: signal.signal,
      }
      for (const days of WINDOWS) {
        const metric = signal.windows.find((w) => w.window_days === days)
        row[`${days}d`] = metric?.avg_return_pct ?? 0
      }
      row.direction = signal.direction
      return row
    })
  }, [summary?.signals])

  const hitRateData = useMemo(() => {
    return (summary?.signals ?? []).map((signal) => {
      const metric30 = signal.windows.find((w) => w.window_days === 30)
      return {
        signal: signal.signal,
        hitRate: (metric30?.hit_rate ?? 0) * 100,
        direction: signal.direction,
      }
    })
  }, [summary?.signals])

  if (isLoading) {
    return (
      <div className="p-3 sm:p-6 space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    )
  }

  if (isError || !summary) {
    return (
      <div className="p-3 sm:p-6 space-y-3">
        <h1 className="text-xl sm:text-2xl font-bold">{t("backtest.title")}</h1>
        <p className="text-sm text-destructive">{t("backtest.error")}</p>
      </div>
    )
  }

  return (
    <div className="p-3 sm:p-6 space-y-4">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold">{t("backtest.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("backtest.caption")}</p>
        <div className="mt-1 flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {t("backtest.computed_at", { time: formatLocalTime(summary.computed_at) })}
          </p>
          {hasSignals && (
            <Button variant="outline" size="sm" onClick={handleExportCsv}>
              <Download className="h-4 w-4 mr-1" />
              {t("backtest.export_csv")}
            </Button>
          )}
        </div>
      </div>

      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("backtest.sop.title")}</span>
          <span className="text-muted-foreground text-xs">{sopOpen ? "▲" : "▼"}</span>
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("backtest.sop.content")}
            </div>
          </div>
        )}
      </div>

      {showBackfillingState ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("backtest.backfilling")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-3 w-full" />
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {t("backtest.backfilling_progress", {
                completed: completedStocks,
                total: totalStocks,
              })}
            </p>
          </CardContent>
        </Card>
      ) : showEmptyState ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {t("backtest.no_data")}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {summary.signals.map((signal) => {
              const metric30 = signal.windows.find((w) => w.window_days === 30)
              return (
                <Card key={signal.signal} className="border-border">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span>{signal.signal}</span>
                      <span
                        className={cn(
                          "rounded px-2 py-0.5 text-[10px] uppercase",
                          signal.confidence === "high" &&
                            "bg-emerald-500/20 text-emerald-400",
                          signal.confidence === "medium" &&
                            "bg-amber-500/20 text-amber-300",
                          signal.confidence === "low" && "bg-zinc-500/20 text-zinc-300",
                        )}
                      >
                        {signal.confidence}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-xs">
                    <p>
                      {t("backtest.card.direction")}: {signal.direction}
                    </p>
                    <p>
                      {t("backtest.card.hit_rate_30d")}:{" "}
                      {((metric30?.hit_rate ?? 0) * 100).toFixed(1)}%
                    </p>
                    <p>
                      {t("backtest.card.avg_return_30d")}:{" "}
                      {(metric30?.avg_return_pct ?? 0).toFixed(2)}%
                    </p>
                    <p>
                      {t("backtest.card.samples_30d")}: {metric30?.sample_count ?? 0}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t("backtest.forward_returns_title")}</CardTitle>
            </CardHeader>
            <CardContent className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={forwardReturnData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.gridColor} />
                  <XAxis dataKey="signal" tick={{ fill: theme.tickColor, fontSize: 11 }} />
                  <YAxis tick={{ fill: theme.tickColor, fontSize: 11 }} />
                  <Tooltip contentStyle={theme.tooltipStyle} />
                  <Bar dataKey="5d" fill="#60a5fa" />
                  <Bar dataKey="10d" fill="#34d399" />
                  <Bar dataKey="30d" fill="#f59e0b" />
                  <Bar dataKey="60d" fill="#a78bfa" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("backtest.hit_rate_title")}</CardTitle>
            </CardHeader>
            <CardContent className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={hitRateData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.gridColor} />
                  <XAxis type="number" tick={{ fill: theme.tickColor, fontSize: 11 }} />
                  <YAxis
                    dataKey="signal"
                    type="category"
                    tick={{ fill: theme.tickColor, fontSize: 11 }}
                    width={120}
                  />
                  <Tooltip
                    contentStyle={theme.tooltipStyle}
                    formatter={(value: number | string | undefined) =>
                      `${Number(value ?? 0).toFixed(1)}%`
                    }
                  />
                  <Bar dataKey="hitRate">
                    {hitRateData.map((entry) => (
                      <Cell key={entry.signal} fill={signalColor(entry.direction)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("backtest.occurrences_title")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2 flex-wrap">
                {summary.signals.map((signal) => (
                  <Button
                    key={signal.signal}
                    variant={currentSignal === signal.signal ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveSignal(signal.signal)}
                    className="min-h-[40px]"
                  >
                    {signal.signal}
                  </Button>
                ))}
              </div>

              <div className="overflow-x-auto border rounded-md">
                <table className="w-full text-xs">
                  <thead className="bg-muted/30">
                    <tr>
                      <th className="text-left px-3 py-2">{t("backtest.table.ticker")}</th>
                      <th className="text-left px-3 py-2">
                        {t("backtest.table.signal_date")}
                      </th>
                      <th className="text-left px-3 py-2">
                        {t("backtest.table.market_status")}
                      </th>
                      {WINDOWS.map((days) => (
                        <th key={days} className="text-right px-3 py-2">
                          {days}d
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(detail?.occurrences ?? []).map((occ, idx) => (
                      <tr
                        key={`${occ.ticker}-${occ.signal_date}-${idx}`}
                        className="border-t border-border"
                      >
                        <td className="px-3 py-2">{occ.ticker}</td>
                        <td className="px-3 py-2">{occ.signal_date}</td>
                        <td className="px-3 py-2">{occ.market_status}</td>
                        {WINDOWS.map((days) => {
                          const value = occ.forward_returns?.[`${days}d`]
                          return (
                            <td key={days} className="px-3 py-2 text-right">
                              {value == null ? "-" : `${value.toFixed(2)}%`}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
