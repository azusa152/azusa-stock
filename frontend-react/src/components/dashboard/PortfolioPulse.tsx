import { useTranslation } from "react-i18next"
import Plot from "react-plotly.js"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { usePrivacyMode, maskMoney } from "@/hooks/usePrivacyMode"
import type {
  RebalanceResponse,
  FearGreedResponse,
  TwrResponse,
  Snapshot,
  LastScanResponse,
  Stock,
  EnrichedStock,
} from "@/api/types/dashboard"

const FEAR_GREED_BANDS = [
  { range: [0, 25] as [number, number], color: "#ef4444" },
  { range: [25, 45] as [number, number], color: "#f97316" },
  { range: [45, 55] as [number, number], color: "#eab308" },
  { range: [55, 75] as [number, number], color: "#86efac" },
  { range: [75, 100] as [number, number], color: "#22c55e" },
]

function computeHealthScore(
  stocks: Stock[],
  enrichedSignalMap: Record<string, string>,
): { pct: number; normal: number; total: number } {
  const active = stocks.filter((s) => s.is_active)
  const total = active.length
  if (total === 0) return { pct: 0, normal: 0, total: 0 }
  const normal = active.filter((s) => {
    const signal = enrichedSignalMap[s.ticker] ?? s.last_scan_signal ?? "NORMAL"
    return signal === "NORMAL"
  }).length
  return { pct: (normal / total) * 100, normal, total }
}


function healthScoreColor(pct: number): string {
  if (pct >= 80) return "text-green-500"
  if (pct >= 50) return "text-yellow-500"
  return "text-red-500"
}

interface Props {
  rebalance?: RebalanceResponse | null
  fearGreed?: FearGreedResponse | null
  twr?: TwrResponse | null
  snapshots?: Snapshot[]
  lastScan?: LastScanResponse | null
  stocks?: Stock[]
  enrichedStocks?: EnrichedStock[]
  holdings?: { id: number }[]
  isLoading: boolean
}

function SparklineMini({ snapshots }: { snapshots: Snapshot[] }) {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 30)
  const cutoffStr = cutoff.toISOString().slice(0, 10)
  const recent = snapshots.filter((s) => s.snapshot_date >= cutoffStr)
  if (recent.length < 2) return null

  const dates = recent.map((s) => s.snapshot_date)
  const values = recent.map((s) => s.total_value)
  const isUp = values[values.length - 1] >= values[0]
  const color = isUp ? "#22c55e" : "#ef4444"
  const fill = isUp ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)"
  const vMin = Math.min(...values)
  const vMax = Math.max(...values)
  const pad = (vMax - vMin) * 0.1 || vMax * 0.01

  return (
    <Plot
      data={[
        {
          x: dates,
          y: values,
          type: "scatter",
          mode: "lines",
          line: { color, width: 1.5 },
          fill: "tozeroy",
          fillcolor: fill,
          hoverinfo: "skip",
        },
      ]}
      layout={{
        height: 60,
        margin: { l: 0, r: 0, t: 0, b: 0 },
        xaxis: { visible: false },
        yaxis: { visible: false, range: [vMin - pad, vMax + pad] },
        showlegend: false,
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%" }}
    />
  )
}

export function PortfolioPulse({
  rebalance,
  fearGreed,
  twr,
  snapshots = [],
  lastScan,
  stocks = [],
  enrichedStocks = [],
  holdings = [],
  isLoading,
}: Props) {
  const { t } = useTranslation()
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="grid grid-cols-3 gap-4 p-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-40" />
              <Skeleton className="h-4 w-32" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  const enrichedSignalMap: Record<string, string> = {}
  for (const es of enrichedStocks) {
    if (es.ticker) {
      enrichedSignalMap[es.ticker] = es.computed_signal ?? es.last_scan_signal ?? "NORMAL"
    }
  }

  const { pct: healthPct, normal: normalCnt, total: totalCnt } = computeHealthScore(
    stocks,
    enrichedSignalMap,
  )

  const stockCount = stocks.filter((s) => s.is_active).length
  const holdingCount = holdings.length
  const marketStatus = lastScan?.market_status
  const sentimentLabel = !marketStatus
    ? t("config.sentiment.not_scanned")
    : marketStatus === "POSITIVE"
      ? t("config.sentiment.positive")
      : marketStatus === "CAUTION"
        ? t("config.sentiment.caution")
        : marketStatus

  // Left column data
  const totalVal = rebalance?.total_value
  const changePct = rebalance?.total_value_change_pct
  const changeAmt = rebalance?.total_value_change
  const ytdTwr = twr?.twr_pct

  // Center column data
  const fgScore = fearGreed?.composite_score ?? 50
  const fgLevel = fearGreed?.composite_level ?? "N/A"
  const vixVal = fearGreed?.vix?.value
  const vixChange = fearGreed?.vix?.change_1d
  const cnnScore = fearGreed?.cnn?.score

  const gaugeTitle = fgLevel.includes(" ") ? fgLevel.split(" ").slice(1).join(" ") : fgLevel

  return (
    <Card>
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
        {/* Left: Total Portfolio Value */}
        <div className="space-y-1 md:col-span-1">
          <p className="text-xs text-muted-foreground">{t("dashboard.total_market_value")}</p>
          {totalVal != null ? (
            <>
              <p className="text-3xl font-bold tabular-nums">
                {maskMoney(totalVal)}
              </p>
              {changePct != null && changeAmt != null && (
                <p
                  className={`text-sm font-medium ${changePct >= 0 ? "text-green-500" : "text-red-500"}`}
                >
                  {changePct >= 0 ? "▲" : "▼"}
                  {Math.abs(changePct).toFixed(2)}%
                  {!isPrivate && ` ($${Math.abs(changeAmt).toLocaleString("en-US", { minimumFractionDigits: 2 })})`}
                </p>
              )}
              {ytdTwr != null && (
                <p
                  className={`text-sm ${ytdTwr >= 0 ? "text-green-500" : "text-red-500"}`}
                >
                  {t("dashboard.ytd_return")} {ytdTwr >= 0 ? "▲" : "▼"}
                  {Math.abs(ytdTwr).toFixed(2)}%
                </p>
              )}
              {snapshots.length >= 2 && !isPrivate && (
                <SparklineMini snapshots={snapshots} />
              )}
            </>
          ) : (
            <p className="text-2xl font-bold text-muted-foreground">N/A</p>
          )}
        </div>

        {/* Center: Fear & Greed Gauge */}
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground text-center">{t("dashboard.fear_greed_title")}</p>
          {fearGreed ? (
            <>
              <Plot
                data={[
                  {
                    type: "indicator",
                    mode: "gauge+number",
                    value: fgScore,
                    title: { text: gaugeTitle, font: { size: 14 } },
                    number: { suffix: "/100", font: { size: 22 } },
                    gauge: {
                      axis: { range: [0, 100], tickwidth: 1 },
                      bar: { color: "#333333" },
                      steps: FEAR_GREED_BANDS.map((b) => ({
                        range: b.range,
                        color: b.color,
                      })),
                    },
                  } as Plotly.Data,
                ]}
                layout={{
                  height: 180,
                  margin: { l: 10, r: 10, t: 30, b: 5 },
                  plot_bgcolor: "rgba(0,0,0,0)",
                  paper_bgcolor: "rgba(0,0,0,0)",
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: "100%" }}
              />
              <p className="text-xs text-muted-foreground text-center">
                {vixVal != null && (
                  <>
                    VIX={vixVal.toFixed(1)}
                    {vixChange != null && ` (${vixChange > 0 ? "▲" : "▼"}${Math.abs(vixChange).toFixed(1)})`}
                  </>
                )}
                {vixVal != null && " ｜ "}
                {cnnScore != null ? `CNN=${cnnScore}` : t("config.fear_greed.cnn_unavailable")}
              </p>
            </>
          ) : (
            <p className="text-center text-muted-foreground text-sm">N/A</p>
          )}
        </div>

        {/* Right: Market Sentiment + Health Score + Tracking */}
        <div className="space-y-4">
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.market_sentiment")}</p>
            <p className="text-lg font-semibold">{sentimentLabel}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.health_score")}</p>
            {totalCnt > 0 ? (
              <>
                <p className={`text-lg font-semibold ${healthScoreColor(healthPct)}`}>
                  {healthPct.toFixed(0)}%
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("dashboard.health_delta", { normal: normalCnt, total: totalCnt })}
                </p>
              </>
            ) : (
              <p className="text-lg font-semibold text-muted-foreground">N/A</p>
            )}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.kpi.tracking_holdings")}</p>
            <p className="text-sm font-medium">
              {t("dashboard.kpi.tracking_holdings_value", {
                stocks: stockCount,
                holdings: holdingCount,
              })}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
