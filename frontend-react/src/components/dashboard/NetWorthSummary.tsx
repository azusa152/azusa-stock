import { useCallback, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { AreaSeries, type IChartApi } from "lightweight-charts"
import { Link } from "react-router-dom"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import { usePrivacyMode, maskMoney } from "@/hooks/usePrivacyMode"
import type { NetWorthSnapshotResponse, NetWorthSummaryResponse } from "@/api/types/networth"

interface Props {
  summary?: NetWorthSummaryResponse | null
  history?: NetWorthSnapshotResponse[]
  isLoading: boolean
}

function NetWorthSparkline({ history }: { history: NetWorthSnapshotResponse[] }) {
  const recent = useMemo(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - 30)
    const cutoffStr = cutoff.toISOString().slice(0, 10)
    return history.filter((s) => s.snapshot_date >= cutoffStr)
  }, [history])

  const isUp = recent.length >= 2 && recent[recent.length - 1].net_worth >= recent[0].net_worth

  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { vertLine: { visible: false }, horzLine: { visible: false } },
        grid: { vertLines: { visible: false }, horzLines: { visible: false } },
        timeScale: { visible: false },
        rightPriceScale: { visible: false },
        handleScroll: false,
        handleScale: false,
      })
      const series = chart.addSeries(AreaSeries, {
        lineColor: isUp ? "#22c55e" : "#ef4444",
        topColor: isUp ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.25)",
        bottomColor: "rgba(0,0,0,0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
      series.setData(
        recent.map((point) => ({
          time: point.snapshot_date as `${number}-${number}-${number}`,
          value: point.net_worth,
        })),
      )
    },
    [recent, isUp],
  )

  if (recent.length < 2) return null
  return <LightweightChartWrapper height={56} onInit={onInit} />
}

export function NetWorthSummary({ summary, history = [], isLoading }: Props) {
  const { t } = useTranslation()
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6 space-y-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-8 w-52" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-14 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!summary) return null

  const grossBase = summary.investment_value + summary.other_assets_value + summary.liabilities_value
  const invPct = grossBase > 0 ? (summary.investment_value / grossBase) * 100 : 0
  const otherPct = grossBase > 0 ? (summary.other_assets_value / grossBase) * 100 : 0
  const liabPct = grossBase > 0 ? (summary.liabilities_value / grossBase) * 100 : 0
  const hasAnyValue =
    summary.items.length > 0 ||
    summary.investment_value > 0 ||
    summary.other_assets_value > 0 ||
    summary.liabilities_value > 0

  return (
    <Card>
      <CardContent className="p-6 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{t("dashboard.net_worth_title")}</p>
          <Button asChild size="sm" variant="outline" className="text-xs min-h-[36px]">
            <Link to="/allocation?tab=net-worth">{t("dashboard.net_worth_manage")}</Link>
          </Button>
        </div>

        {hasAnyValue ? (
          <>
            <p className="text-3xl font-bold tabular-nums">{maskMoney(summary.net_worth)}</p>
            <p className="text-xs text-muted-foreground">
              {!isPrivate &&
                new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: summary.display_currency,
                  minimumFractionDigits: 2,
                }).format(summary.net_worth)}
            </p>
            <p className="text-xs text-muted-foreground">{t("net_worth.summary_formula")}</p>

            <div className="h-2 w-full rounded-full overflow-hidden bg-muted/40 flex">
              <div className="h-full bg-blue-500" style={{ width: `${invPct}%` }} />
              <div className="h-full bg-green-500" style={{ width: `${otherPct}%` }} />
              <div className="h-full bg-red-500" style={{ width: `${liabPct}%` }} />
            </div>

            <div className="grid grid-cols-3 gap-2 text-[11px] text-muted-foreground">
              <p>{t("net_worth.segment_investments")} {invPct.toFixed(0)}%</p>
              <p>{t("net_worth.segment_assets")} {otherPct.toFixed(0)}%</p>
              <p>{t("net_worth.segment_liabilities")} {liabPct.toFixed(0)}%</p>
            </div>

            {!isPrivate && <NetWorthSparkline history={history} />}
          </>
        ) : (
          <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
            {t("net_worth.empty")}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
