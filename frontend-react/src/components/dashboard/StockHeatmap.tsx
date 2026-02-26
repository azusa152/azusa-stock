import { useTranslation } from "react-i18next"
import { Treemap, Tooltip, ResponsiveContainer } from "recharts"
import type { EnrichedStock } from "@/api/types/dashboard"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { HEATMAP_COLORS } from "@/lib/constants"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  enrichedStocks: EnrichedStock[]
  isLoading?: boolean
}

function inferCurrencySymbol(ticker: string): string {
  if (ticker.endsWith(".TW")) return "NT$"
  if (ticker.endsWith(".T")) return "¥"
  if (ticker.endsWith(".HK")) return "HK$"
  return "$"
}

function getChangeColor(changePct: number | undefined | null): string {
  if (changePct == null) return HEATMAP_COLORS.neutral
  if (changePct >= 3) return HEATMAP_COLORS.strongGain
  if (changePct >= 1.5) return HEATMAP_COLORS.gain
  if (changePct >= 0.3) return HEATMAP_COLORS.weakGain
  if (changePct > -0.3) return HEATMAP_COLORS.neutral
  if (changePct > -1.5) return HEATMAP_COLORS.weakLoss
  if (changePct > -3) return HEATMAP_COLORS.loss
  return HEATMAP_COLORS.strongLoss
}

interface TreemapLeaf {
  [key: string]: unknown
  name: string
  size: number
  ticker: string
  changePct: number | null
  price: number | null
  rsi: number | null
  sector: string
  // `fill` is the standard Recharts key for custom cell color in Treemap
  fill: string
}

interface TreemapNode {
  [key: string]: unknown
  name: string
  children: TreemapLeaf[]
}

interface CellContentProps {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  changePct?: number | null
  // Recharts injects data keys as props; `fill` is forwarded from the leaf data
  fill?: string
}

function HeatCell({ x = 0, y = 0, width = 0, height = 0, name, changePct, fill = HEATMAP_COLORS.neutral }: CellContentProps) {
  if (width < 8 || height < 8) return null
  const showText = width > 36 && height > 22
  const showChange = width > 44 && height > 38 && changePct != null
  const sign = (changePct ?? 0) >= 0 ? "+" : ""

  return (
    <g>
      <rect x={x + 1} y={y + 1} width={width - 2} height={height - 2} fill={fill} rx={3} />
      {showText && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showChange ? 7 : 0)}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={Math.min(12, Math.max(9, width / 6))}
          fontWeight={600}
        >
          {name}
        </text>
      )}
      {showChange && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 9}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="rgba(255,255,255,0.85)"
          fontSize={Math.min(10, Math.max(8, width / 7))}
        >
          {sign}{changePct!.toFixed(2)}%
        </text>
      )}
    </g>
  )
}

interface TooltipPayload {
  ticker?: string
  sector?: string
  changePct?: number | null
  price?: number | null
  rsi?: number | null
}

function HeatmapTooltip({
  active,
  payload,
  theme,
  t,
}: {
  active?: boolean
  payload?: { payload?: TooltipPayload }[]
  theme: ReturnType<typeof useRechartsTheme>
  t: (key: string) => string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d?.ticker) return null
  const sign = (d.changePct ?? 0) >= 0 ? "+" : ""
  const currencySymbol = inferCurrencySymbol(d.ticker)

  return (
    <div style={{ ...theme.tooltipStyle, padding: "8px 12px", minWidth: 140 }}>
      <p style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{d.ticker}</p>
      {d.sector && (
        <p style={{ fontSize: 11, color: theme.tooltipText, opacity: 0.7, marginBottom: 2 }}>{d.sector}</p>
      )}
      {d.price != null && (
        <p style={{ fontSize: 11, marginBottom: 2 }}>
          {t("dashboard.heatmap_price")}: <strong>{currencySymbol}{d.price.toFixed(2)}</strong>
        </p>
      )}
      {d.changePct != null && (
        <p style={{ fontSize: 11, marginBottom: 2, color: d.changePct >= 0 ? HEATMAP_COLORS.gain : HEATMAP_COLORS.loss }}>
          {t("dashboard.heatmap_change")}: <strong>{sign}{d.changePct.toFixed(2)}%</strong>
        </p>
      )}
      {d.rsi != null && (
        <p style={{ fontSize: 11 }}>RSI: <strong>{d.rsi.toFixed(1)}</strong></p>
      )}
    </div>
  )
}

export function StockHeatmap({ enrichedStocks, isLoading }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  const title = t("dashboard.heatmap_title")

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[320px] w-full" />
        </CardContent>
      </Card>
    )
  }

  const stocks = enrichedStocks.filter(
    (s) => s.price != null || s.change_pct != null
  )

  if (!stocks.length) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{t("dashboard.heatmap_empty")}</p>
        </CardContent>
      </Card>
    )
  }

  // Group by sector; stocks without sector go to "Other"
  const sectorMap = new Map<string, EnrichedStock[]>()
  for (const s of stocks) {
    const sector = s.sector ?? "Other"
    if (!sectorMap.has(sector)) sectorMap.set(sector, [])
    sectorMap.get(sector)!.push(s)
  }

  // Sort sectors: larger groups first, "Other" always last
  const sortedSectors = [...sectorMap.entries()].sort(([sectorA, stocksA], [sectorB, stocksB]) => {
    if (sectorA === "Other") return 1
    if (sectorB === "Other") return -1
    return stocksB.length - stocksA.length
  })

  const treeData: TreemapNode[] = sortedSectors.map(([sector, sectorStocks]) => ({
    name: sector,
    children: sectorStocks.map((s) => ({
      name: s.ticker,
      size: 1,
      ticker: s.ticker,
      changePct: s.change_pct ?? null,
      price: s.price ?? null,
      rsi: s.rsi ?? null,
      sector,
      fill: getChangeColor(s.change_pct),
    })),
  }))

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground pb-2">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: HEATMAP_COLORS.strongLoss }} />
            ≤ −3%
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: HEATMAP_COLORS.neutral }} />
            ≈ 0%
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: HEATMAP_COLORS.strongGain }} />
            ≥ +3%
          </span>
          <span className="text-muted-foreground/60">· {t("dashboard.heatmap_grouped_by")}</span>
        </div>
        <ResponsiveContainer width="100%" height={320}>
          <Treemap
            data={treeData}
            dataKey="size"
            content={<HeatCell />}
          >
            <Tooltip content={<HeatmapTooltip theme={theme} t={t} />} />
          </Treemap>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
