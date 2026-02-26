import { useCallback, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { AreaSeries, type IChartApi } from "lightweight-charts"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { usePrivacyMode, maskMoney } from "@/hooks/usePrivacyMode"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import { InfoPopover } from "./InfoPopover"
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
  { range: [0, 25] as [number, number], color: "#ef4444", label: "EF" },
  { range: [25, 45] as [number, number], color: "#f97316", label: "F" },
  { range: [45, 55] as [number, number], color: "#eab308", label: "N" },
  { range: [55, 75] as [number, number], color: "#86efac", label: "G" },
  { range: [75, 100] as [number, number], color: "#22c55e", label: "EG" },
]

const LEGACY_SENTIMENT_MAP: Record<string, string> = {
  positive: "bullish",
  caution: "bearish",
}

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

/** Semi-circle SVG gauge for Fear & Greed (0-100). */
function FearGreedGauge({ score, level }: { score: number; level: string }) {
  const cx = 100
  const cy = 100
  const r = 70
  const strokeW = 16

  // Arc helper: polar to cartesian on the semicircle (180° to 0°, left to right)
  function polarToCartesian(angleDeg: number) {
    const rad = (angleDeg * Math.PI) / 180
    return {
      x: cx + r * Math.cos(Math.PI - rad),
      y: cy - r * Math.sin(Math.PI - rad),
    }
  }

  // Draw arc segment from score pct1 to pct2 (0-100) along the semicircle
  function arcPath(pct1: number, pct2: number) {
    const a1 = (pct1 / 100) * 180
    const a2 = (pct2 / 100) * 180
    const p1 = polarToCartesian(a1)
    const p2 = polarToCartesian(a2)
    const largeArc = a2 - a1 > 180 ? 1 : 0
    return `M ${p1.x} ${p1.y} A ${r} ${r} 0 ${largeArc} 1 ${p2.x} ${p2.y}`
  }

  // Needle
  const needleAngleDeg = (score / 100) * 180
  const needleBase1 = polarToCartesian(needleAngleDeg - 5)
  const needleBase2 = polarToCartesian(needleAngleDeg + 5)
  // Tip stays within the arc radius
  const tipX = cx + (r - strokeW / 2 - 4) * Math.cos(Math.PI - (needleAngleDeg * Math.PI) / 180)
  const tipY = cy - (r - strokeW / 2 - 4) * Math.sin(Math.PI - (needleAngleDeg * Math.PI) / 180)

  // Label display
  const gaugeTitle = level.includes(" ") ? level.split(" ").slice(1).join(" ") : level

  return (
    <svg viewBox="0 0 200 110" className="w-full" style={{ maxHeight: 160 }}>
      {/* Background arc */}
      <path
        d={arcPath(0, 100)}
        fill="none"
        stroke="rgba(128,128,128,0.15)"
        strokeWidth={strokeW}
        strokeLinecap="butt"
      />

      {/* Colored band arcs */}
      {FEAR_GREED_BANDS.map((band) => (
        <path
          key={band.label}
          d={arcPath(band.range[0], band.range[1])}
          fill="none"
          stroke={band.color}
          strokeWidth={strokeW}
          strokeLinecap="butt"
          opacity={0.85}
        />
      ))}

      {/* Needle */}
      <polygon
        points={`${tipX},${tipY} ${needleBase1.x},${needleBase1.y} ${cx},${cy} ${needleBase2.x},${needleBase2.y}`}
        fill="currentColor"
        opacity={0.7}
      />
      <circle cx={cx} cy={cy} r={5} fill="currentColor" opacity={0.7} />

      {/* Score */}
      <text x={cx} y={cy - 18} textAnchor="middle" fontSize={22} fontWeight="bold" fill="currentColor">
        {score}
      </text>
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.6}>
        /100
      </text>

      {/* Level label */}
      <text x={cx} y={cy + 16} textAnchor="middle" fontSize={11} fill="currentColor" opacity={0.75}>
        {gaugeTitle}
      </text>
    </svg>
  )
}

function scoreToColor(score: number): string {
  if (!Number.isFinite(score)) return FEAR_GREED_BANDS[FEAR_GREED_BANDS.length - 1].color
  const clamped = Math.max(0, Math.min(100, score))
  for (const band of FEAR_GREED_BANDS) {
    if (clamped >= band.range[0] && clamped <= band.range[1]) return band.color
  }
  return FEAR_GREED_BANDS[FEAR_GREED_BANDS.length - 1].color
}

interface ComponentBarsProps {
  components: FearGreedResponse["components"]
}

function FearGreedComponentBars({ components }: ComponentBarsProps) {
  const { t } = useTranslation()
  if (!components || components.length === 0) return null

  return (
    <div className="mt-2 space-y-1">
      {components.map((c) => {
        const score = c.score
        const label = t(`config.fear_greed.components.${c.name}`, { defaultValue: c.name })
        const weightPct = Math.round(c.weight * 100)
        return (
          <div key={c.name} className="flex items-center gap-2">
            <span className="w-24 shrink-0 text-right text-[10px] text-muted-foreground leading-none">
              {label}
            </span>
            <div className="relative flex-1 h-2 rounded-full overflow-hidden bg-muted/40">
              {score != null ? (
                <div
                  className="absolute left-0 top-0 h-full rounded-full transition-all"
                  style={{ width: `${score}%`, backgroundColor: scoreToColor(score) }}
                />
              ) : (
                <div className="absolute left-0 top-0 h-full w-full bg-muted/20" />
              )}
            </div>
            <span className="w-7 shrink-0 text-[10px] text-muted-foreground tabular-nums">
              {score != null ? score : "–"}
            </span>
            <span className="w-7 shrink-0 text-[10px] text-muted-foreground/50 tabular-nums">
              {weightPct}%
            </span>
          </div>
        )
      })}
    </div>
  )
}

function SparklineMini({ snapshots }: { snapshots: Snapshot[] }) {
  const { recent, isUp } = useMemo(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - 30)
    const cutoffStr = cutoff.toISOString().slice(0, 10)
    const r = snapshots.filter((s) => s.snapshot_date >= cutoffStr)
    const vals = r.map((s) => s.total_value)
    return { recent: r, isUp: vals.length >= 2 && vals[vals.length - 1] >= vals[0] }
  }, [snapshots])

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
        recent.map((s) => ({
          time: s.snapshot_date as `${number}-${number}-${number}`,
          value: s.total_value,
        })),
      )
    },
    [recent, isUp],
  )

  if (recent.length < 2) return null

  return <LightweightChartWrapper height={60} onInit={onInit} />
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
        <CardContent className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-3">
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
  const rawKey = marketStatus?.toLowerCase() ?? ""
  const sentimentKey = LEGACY_SENTIMENT_MAP[rawKey] ?? rawKey
  const sentimentLabel = !marketStatus
    ? t("config.sentiment.not_scanned")
    : t(`config.sentiment.${sentimentKey}`, { defaultValue: marketStatus })

  const displayCurrency = rebalance?.display_currency ?? "USD"
  const totalVal = rebalance?.total_value
  const changePct = rebalance?.total_value_change_pct
  const changeAmt = rebalance?.total_value_change
  const ytdTwr = twr?.twr_pct

  const fgScore = fearGreed?.composite_score ?? 50
  const fgLevel = fearGreed?.composite_level ?? "N/A"
  const vixVal = fearGreed?.vix?.value
  const vixChange = fearGreed?.vix?.change_1d
  const cnnScore = fearGreed?.cnn?.score

  const allNonNormalStocks = stocks
    .filter((s) => s.is_active)
    .flatMap((s) => {
      const signal = enrichedSignalMap[s.ticker] ?? s.last_scan_signal ?? "NORMAL"
      return signal !== "NORMAL" ? [{ ticker: s.ticker, signal }] : []
    })
  const NON_NORMAL_CAP = 10
  const nonNormalStocks = allNonNormalStocks.slice(0, NON_NORMAL_CAP)
  const nonNormalOverflow = allNonNormalStocks.length - nonNormalStocks.length

  const fearGreedTopBottom = (() => {
    const components = fearGreed?.components
    if (!components || components.length === 0) return null
    const scored = components.filter((c) => c.score != null) as Array<{ name: string; score: number; weight: number }>
    if (scored.length === 0) return null
    const sorted = [...scored].sort((a, b) => b.score - a.score)
    const topName = sorted[0].name
    const bottomName = sorted[sorted.length - 1].name
    return {
      top: {
        label: t(`config.fear_greed.components.${topName}`, { defaultValue: topName }),
        score: sorted[0].score,
      },
      bottom: {
        label: t(`config.fear_greed.components.${bottomName}`, { defaultValue: bottomName }),
        score: sorted[sorted.length - 1].score,
      },
    }
  })()

  return (
    <Card>
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
        {/* Left: Total Portfolio Value */}
        <div className="space-y-1 md:col-span-1">
          <p className="text-xs text-muted-foreground">{t("dashboard.total_market_value")}</p>
          {totalVal != null ? (
            <>
              <p className="text-3xl font-bold tabular-nums">{maskMoney(totalVal)}</p>
              {changePct != null && changeAmt != null && (
                <p className={`text-sm font-medium ${changePct >= 0 ? "text-green-500" : "text-red-500"}`}>
                  {changePct >= 0 ? "▲" : "▼"}
                  {Math.abs(changePct).toFixed(2)}%
                  {!isPrivate && ` (${new Intl.NumberFormat("en-US", { style: "currency", currency: displayCurrency, minimumFractionDigits: 2 }).format(Math.abs(changeAmt))})`}
                </p>
              )}
              {ytdTwr != null && (
                <p className={`text-sm ${ytdTwr >= 0 ? "text-green-500" : "text-red-500"}`}>
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
          <div className="flex items-center justify-center gap-1">
            <p className="text-xs text-muted-foreground">{t("dashboard.fear_greed_title")}</p>
            {fearGreed && (
              <InfoPopover align="center">
                <p className="text-xs font-medium">
                  {fearGreed.cnn?.score != null
                    ? t("dashboard.info.fear_greed_source_cnn")
                    : fearGreed.self_calculated_score != null
                      ? t("dashboard.info.fear_greed_source_self")
                      : t("dashboard.info.fear_greed_source_vix")}
                </p>
                {fearGreedTopBottom && (
                  <>
                    <p className="text-xs text-muted-foreground">
                      {t("dashboard.info.fear_greed_top", {
                        name: fearGreedTopBottom.top.label,
                        score: fearGreedTopBottom.top.score,
                      })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("dashboard.info.fear_greed_bottom", {
                        name: fearGreedTopBottom.bottom.label,
                        score: fearGreedTopBottom.bottom.score,
                      })}
                    </p>
                  </>
                )}
              </InfoPopover>
            )}
          </div>
          {fearGreed ? (
            <>
              <FearGreedGauge score={fgScore} level={fgLevel} />
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
              {fearGreed.components && fearGreed.components.length > 0 && (
                <FearGreedComponentBars components={fearGreed.components} />
              )}
            </>
          ) : (
            <p className="text-center text-muted-foreground text-sm">N/A</p>
          )}
        </div>

        {/* Right: Market Sentiment + Health Score + Tracking */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-1">
              <p className="text-xs text-muted-foreground">{t("dashboard.market_sentiment")}</p>
              <InfoPopover align="end">
                {lastScan?.market_status_details ? (
                  <p className="text-xs">{lastScan.market_status_details}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">{t("dashboard.info.sentiment_no_details")}</p>
                )}
                <p className="text-xs text-muted-foreground whitespace-pre-line">
                  {t("dashboard.info.sentiment_thresholds")}
                </p>
              </InfoPopover>
            </div>
            <p className="text-lg font-semibold">{sentimentLabel}</p>
          </div>
          <div>
            <div className="flex items-center gap-1">
              <p className="text-xs text-muted-foreground">{t("dashboard.health_score")}</p>
              <InfoPopover align="end">
                {nonNormalStocks.length > 0 ? (
                  <>
                    <p className="text-xs font-medium">{t("dashboard.info.health_non_normal")}</p>
                    <ul className="space-y-0.5">
                      {nonNormalStocks.map(({ ticker, signal }) => (
                        <li key={ticker} className="text-xs flex gap-1.5">
                          <span className="font-medium">{ticker}</span>
                          <span className="text-muted-foreground">{signal}</span>
                        </li>
                      ))}
                    </ul>
                    {nonNormalOverflow > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {t("dashboard.info.health_overflow", { count: nonNormalOverflow })}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-xs">{t("dashboard.info.health_all_normal")}</p>
                )}
              </InfoPopover>
            </div>
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
