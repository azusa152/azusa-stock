import { useMemo, useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useGuruBacktest } from "@/api/hooks/useSmartMoney"
import type { Guru } from "@/api/types/smartMoney"
import { cn } from "@/lib/utils"
import {
  GURU_BACKTEST_BENCHMARK_OPTIONS,
  GURU_BACKTEST_QUARTER_OPTIONS,
} from "@/lib/constants"

export function GuruBacktestTab({
  gurus,
  enabled,
}: {
  gurus: Guru[]
  enabled?: boolean
}) {
  const { t } = useTranslation()
  const [sopOpen, setSopOpen] = useState(false)
  const [selectedGuruId, setSelectedGuruId] = useState<number | null>(gurus[0]?.id ?? null)
  const [selectedQuarters, setSelectedQuarters] = useState<number>(4)
  const [selectedBenchmark, setSelectedBenchmark] = useState<string>("SPY")
  const [runTriggered, setRunTriggered] = useState(false)

  const effectiveGuruId = selectedGuruId ?? gurus[0]?.id ?? null

  const queryEnabled = (enabled ?? true) && runTriggered && !!effectiveGuruId
  const { data, isLoading, isError, error } = useGuruBacktest(
    effectiveGuruId,
    selectedQuarters,
    selectedBenchmark,
    queryEnabled,
  )

  const chartData = useMemo(() => {
    if (!data) return []
    const dates = data.cumulative_series?.dates ?? []
    const cloneReturns = data.cumulative_series?.clone_returns ?? []
    const benchmarkReturns = data.cumulative_series?.benchmark_returns ?? []
    return dates.map((d: string, idx: number) => ({
      date: d,
      clone: cloneReturns[idx] ?? 0,
      benchmark: benchmarkReturns[idx] ?? 0,
    }))
  }, [data])

  const errMsg = (() => {
    if (!error) return ""
    if (typeof error === "object" && error && "detail" in error) {
      return String((error as { detail?: string }).detail ?? "")
    }
    return ""
  })()

  if (gurus.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("smart_money.no_gurus_hint")}</p>
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
        {t("smart_money.backtest.disclaimer")}
      </div>

      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          aria-expanded={sopOpen}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("smart_money.backtest.sop_title")}</span>
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", sopOpen && "rotate-180")} />
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("smart_money.backtest.sop_content")}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">{t("smart_money.backtest.guru_label")}</span>
          <select
            value={effectiveGuruId ?? ""}
            onChange={(event) => setSelectedGuruId(Number(event.target.value))}
            className="h-9 min-h-[44px] rounded-md border border-input bg-background px-2"
          >
            {gurus.map((guru) => (
              <option key={guru.id} value={guru.id}>
                {guru.display_name}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">{t("smart_money.backtest.quarters_label")}</span>
          <select
            value={selectedQuarters}
            onChange={(event) => setSelectedQuarters(Number(event.target.value))}
            className="h-9 min-h-[44px] rounded-md border border-input bg-background px-2"
          >
            {GURU_BACKTEST_QUARTER_OPTIONS.map((quarter) => (
              <option key={quarter} value={quarter}>
                {quarter}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">{t("smart_money.backtest.benchmark_label")}</span>
          <select
            value={selectedBenchmark}
            onChange={(event) => setSelectedBenchmark(event.target.value)}
            className="h-9 min-h-[44px] rounded-md border border-input bg-background px-2"
          >
            {GURU_BACKTEST_BENCHMARK_OPTIONS.map((benchmark) => (
              <option key={benchmark} value={benchmark}>
                {benchmark}
              </option>
            ))}
          </select>
        </label>

        <Button
          onClick={() => setRunTriggered(true)}
          className="h-9"
        >
          {t("smart_money.backtest.run")}
        </Button>
      </div>

      {!runTriggered && (
        <p className="text-sm text-muted-foreground">{t("smart_money.backtest.run_hint")}</p>
      )}

      {isLoading && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{t("smart_money.backtest.computing")}</p>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {isError && (
        <p className="text-sm text-destructive">
          {errMsg || t("smart_money.backtest.error")}
        </p>
      )}

      {data && !isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="rounded-md border p-3">
              <p className="text-muted-foreground">{t("smart_money.backtest.clone_return")}</p>
              <p className="text-base font-semibold">{data.cumulative_clone_return.toFixed(2)}%</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-muted-foreground">{t("smart_money.backtest.benchmark_return")}</p>
              <p className="text-base font-semibold">{data.cumulative_benchmark_return.toFixed(2)}%</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-muted-foreground">{t("smart_money.backtest.alpha")}</p>
              <p className="text-base font-semibold">{data.alpha.toFixed(2)}%</p>
            </div>
          </div>

          <div className="rounded-md border p-2">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={28} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  formatter={(value: number | string | undefined) => {
                    const numeric =
                      typeof value === "number"
                        ? value
                        : Number.parseFloat(String(value ?? 0))
                    return `${numeric.toFixed(2)}%`
                  }}
                />
                <Line type="monotone" dataKey="clone" name={t("smart_money.backtest.clone_line")} stroke="#22c55e" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="benchmark" name={t("smart_money.backtest.benchmark_line")} stroke="#3b82f6" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="text-left py-2 px-2">{t("smart_money.backtest.col.report_date")}</th>
                  <th className="text-left py-2 px-2">{t("smart_money.backtest.col.filing_date")}</th>
                  <th className="text-right py-2 px-2">{t("smart_money.backtest.col.clone_return")}</th>
                  <th className="text-right py-2 px-2">{t("smart_money.backtest.col.benchmark_return")}</th>
                  <th className="text-right py-2 px-2">{t("smart_money.backtest.col.alpha")}</th>
                  <th className="text-right py-2 px-2">{t("smart_money.backtest.col.holdings")}</th>
                </tr>
              </thead>
              <tbody>
                {(data.quarters ?? []).map((quarter) => (
                  <tr
                    key={`${quarter.report_date}-${quarter.filing_date}`}
                    className="border-b border-border/50"
                  >
                    <td className="py-1.5 px-2">{quarter.report_date}</td>
                    <td className="py-1.5 px-2">{quarter.filing_date}</td>
                    <td className="py-1.5 px-2 text-right">{quarter.clone_return_pct.toFixed(2)}%</td>
                    <td className="py-1.5 px-2 text-right">{quarter.benchmark_return_pct.toFixed(2)}%</td>
                    <td className="py-1.5 px-2 text-right">{quarter.alpha_pct.toFixed(2)}%</td>
                    <td className="py-1.5 px-2 text-right">{quarter.holdings_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
