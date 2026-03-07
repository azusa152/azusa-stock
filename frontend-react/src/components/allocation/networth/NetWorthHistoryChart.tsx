import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { CHART_COLOR_PALETTE } from "@/lib/constants"
import type { NetWorthSnapshotResponse } from "@/api/types/networth"

type Timeframe = 30 | 90 | 180 | 365 | 730

interface Props {
  history: NetWorthSnapshotResponse[]
  isLoading: boolean
  privacyMode: boolean
  timeframe: Timeframe
  onTimeframeChange: (value: Timeframe) => void
}

const TIMEFRAMES: Array<{ value: Timeframe; key: string }> = [
  { value: 30, key: "1m" },
  { value: 90, key: "3m" },
  { value: 180, key: "6m" },
  { value: 365, key: "1y" },
  { value: 730, key: "max" },
]

const COLOR_INVESTMENT = CHART_COLOR_PALETTE[0]
const COLOR_OTHER_ASSETS = CHART_COLOR_PALETTE[1]
const COLOR_LIABILITIES = "#ef4444"
const COLOR_NET_WORTH = "#0f172a"

export function NetWorthHistoryChart({
  history,
  isLoading,
  privacyMode,
  timeframe,
  onTimeframeChange,
}: Props) {
  const { t } = useTranslation()

  const data = useMemo(
    () =>
      history.map((point) => ({
        date: point.snapshot_date,
        investment: point.investment_value,
        otherAssets: point.other_assets_value,
        liabilities: -Math.abs(point.liabilities_value),
        netWorth: point.net_worth,
      })),
    [history],
  )

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-4 sm:p-6 space-y-3">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-56 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-4 sm:p-6 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <p className="text-sm font-semibold">{t("net_worth.history_title")}</p>
          <div className="flex items-center gap-1">
            {TIMEFRAMES.map((option) => (
              <Button
                key={option.value}
                type="button"
                size="sm"
                variant={timeframe === option.value ? "default" : "outline"}
                aria-pressed={timeframe === option.value}
                onClick={() => onTimeframeChange(option.value)}
                className="min-h-[32px] px-2 text-[11px]"
              >
                {t(`net_worth.timeframe.${option.key}`)}
              </Button>
            ))}
          </div>
        </div>

        {data.length < 2 ? (
          <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
            {t("net_worth.history_empty")}
          </div>
        ) : (
          <div className="h-64" role="img" aria-label={t("accessibility.chart_net_worth")}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value: unknown) => {
                    const s = String(value ?? "")
                    return s.length >= 5 ? s.slice(5) : s
                  }}
                />
                <YAxis hide={privacyMode} tick={{ fontSize: 11 }} width={72} />
                <Tooltip
                  formatter={(value: number | string | undefined) => {
                    if (privacyMode) return "***"
                    const numeric = typeof value === "number" ? value : Number(value ?? 0)
                    return Number.isFinite(numeric) ? numeric.toFixed(2) : "0.00"
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="investment"
                  stackId="assets"
                  stroke={COLOR_INVESTMENT}
                  fill={COLOR_INVESTMENT}
                  fillOpacity={0.28}
                  name={t("net_worth.segment_investments")}
                />
                <Area
                  type="monotone"
                  dataKey="otherAssets"
                  stackId="assets"
                  stroke={COLOR_OTHER_ASSETS}
                  fill={COLOR_OTHER_ASSETS}
                  fillOpacity={0.24}
                  name={t("net_worth.segment_assets")}
                />
                <Area
                  type="monotone"
                  dataKey="liabilities"
                  stroke={COLOR_LIABILITIES}
                  fill={COLOR_LIABILITIES}
                  fillOpacity={0.24}
                  name={t("net_worth.segment_liabilities")}
                />
                <Area
                  type="monotone"
                  dataKey="netWorth"
                  stroke={COLOR_NET_WORTH}
                  fillOpacity={0}
                  strokeWidth={2}
                  name={t("net_worth.title")}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
