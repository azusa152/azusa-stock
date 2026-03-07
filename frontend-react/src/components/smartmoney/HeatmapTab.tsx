import { useMemo, useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  ResponsiveContainer,
  Tooltip,
  Treemap,
} from "recharts"
import { Skeleton } from "@/components/ui/skeleton"
import { useGuruHeatmap } from "@/api/hooks/useSmartMoney"
import { ACTION_COLORS } from "@/components/smartmoney/formatters"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type ViewMode = "sector" | "guru"

type HeatLeaf = {
  name: string
  ticker: string
  size: number
  actionColor: string
  weightPct: number
  dominantAction: string
  sector: string
  guruNames: string
}

type HeatNode = {
  name: string
  children: HeatLeaf[]
}

type HeatCellProps = {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  actionColor?: string
  weightPct?: number
}

function HeatCell({ x = 0, y = 0, width = 0, height = 0, name = "", actionColor = "#64748b", weightPct = 0 }: HeatCellProps) {
  if (width < 8 || height < 8) return null

  // Vary opacity by weight so same-action cells are still distinguishable.
  const safeWeight = Number.isFinite(weightPct) ? Math.max(0, weightPct) : 0
  const opacity = 0.55 + 0.45 * Math.min(1, Math.sqrt(safeWeight / 15))
  const showText = width > 36 && height > 22
  const showWeight = width > 44 && height > 38 && safeWeight > 0

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={width - 2}
        height={height - 2}
        fill={actionColor}
        fillOpacity={opacity}
        stroke="rgba(255,255,255,0.14)"
        rx={3}
      />
      {showText && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showWeight ? 7 : 0)}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#fff"
          fontSize={Math.min(12, Math.max(9, width / 6))}
          fontWeight={600}
        >
          {name}
        </text>
      )}
      {showWeight && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 9}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="rgba(255,255,255,0.85)"
          fontSize={Math.min(10, Math.max(8, width / 7))}
        >
          {safeWeight.toFixed(1)}%
        </text>
      )}
    </g>
  )
}

function HeatmapTooltip({
  active,
  payload,
  t,
}: {
  active?: boolean
  payload?: { payload?: HeatLeaf }[]
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d?.ticker) return null
  const actionColor = ACTION_COLORS[d.dominantAction] ?? ACTION_COLORS.UNCHANGED

  return (
    <div className="rounded-md border border-slate-500/30 bg-slate-900/95 px-3 py-2 text-xs text-slate-100 shadow-lg">
      <p className="mb-0.5 text-sm font-semibold">{d.ticker}</p>
      <p className="mb-1 text-[11px] text-slate-300">{d.sector}</p>
      <p className="mb-1 flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: actionColor }} />
        <span>{t(`smart_money.action.${d.dominantAction.toLowerCase()}`)}</span>
      </p>
      <p className="mb-1">
        {t("smart_money.col.weight_pct")}: <strong>{d.weightPct.toFixed(2)}%</strong>
      </p>
      <p className="max-w-[260px] text-[11px] text-slate-300">
        {t("smart_money.heatmap.guru_label")}: {d.guruNames}
      </p>
    </div>
  )
}

export function HeatmapTab({ style, enabled }: { style?: string | null; enabled?: boolean }) {
  const { t } = useTranslation()
  const [sectorFilter, setSectorFilter] = useState("all")
  const [viewMode, setViewMode] = useState<ViewMode>("sector")
  const [sopOpen, setSopOpen] = useState(false)
  const { data, isLoading, isError } = useGuruHeatmap(style, enabled ?? true)

  const sectors = useMemo(() => {
    const set = new Set<string>()
    for (const item of data?.items ?? []) {
      if (item.sector) set.add(item.sector)
    }
    return Array.from(set).sort()
  }, [data])

  const filteredItems = useMemo(() => {
    const items = data?.items ?? []
    if (sectorFilter === "all") return items
    return items.filter((item) => (item.sector ?? "Unknown") === sectorFilter)
  }, [data, sectorFilter])

  const dominantActions = useMemo(() => {
    const set = new Set<string>()
    for (const item of filteredItems) {
      if (item.dominant_action) set.add(item.dominant_action)
    }
    return Array.from(set)
  }, [filteredItems])

  const treeData = useMemo(() => {
    if (viewMode === "guru") {
      const byGuru: Record<string, HeatLeaf[]> = {}
      const unknownGuru = t("smart_money.heatmap.unknown_guru")
      for (const item of filteredItems) {
        const sector = item.sector ?? "Unknown"
        const ticker = item.ticker
        const gurus = item.gurus ?? []
        if (gurus.length === 0) {
          byGuru[unknownGuru] ??= []
          byGuru[unknownGuru].push({
            name: ticker,
            ticker,
            size: Math.max(item.combined_weight_pct ?? 0.001, 0.001),
            actionColor: ACTION_COLORS[item.dominant_action] ?? ACTION_COLORS.UNCHANGED,
            weightPct: item.combined_weight_pct ?? 0,
            dominantAction: item.dominant_action ?? "UNCHANGED",
            sector,
            guruNames: unknownGuru,
          })
          continue
        }
        for (const guru of gurus) {
          const guruName = guru.guru_display_name
          byGuru[guruName] ??= []
          byGuru[guruName].push({
            name: ticker,
            ticker,
            size: Math.max(guru.weight_pct ?? 0.001, 0.001),
            actionColor: ACTION_COLORS[guru.action] ?? ACTION_COLORS.UNCHANGED,
            weightPct: guru.weight_pct ?? 0,
            dominantAction: guru.action ?? "UNCHANGED",
            sector,
            guruNames: guruName,
          })
        }
      }
      return Object.entries(byGuru).map(([name, children]) => ({ name, children })) as HeatNode[]
    }

    const bySector: Record<string, HeatLeaf[]> = {}
    for (const item of filteredItems) {
      const sector = item.sector ?? "Unknown"
      const ticker = item.ticker
      bySector[sector] ??= []
      bySector[sector].push({
        name: ticker,
        ticker,
        size: Math.max(item.combined_weight_pct ?? 0.001, 0.001),
        actionColor: ACTION_COLORS[item.dominant_action] ?? ACTION_COLORS.UNCHANGED,
        weightPct: item.combined_weight_pct ?? 0,
        dominantAction: item.dominant_action ?? "UNCHANGED",
        sector,
        guruNames: (item.gurus ?? []).map((g) => g.guru_display_name).join(", "),
      })
    }
    return Object.entries(bySector).map(([name, children]) => ({ name, children })) as HeatNode[]
  }, [filteredItems, t, viewMode])

  if (isLoading) return <Skeleton className="h-80 w-full" />
  if (isError || !data) {
    return <p className="text-sm text-destructive">{t("common.error_backend")}</p>
  }
  if ((data.items ?? []).length === 0) {
    return <p className="text-sm text-muted-foreground">{t("smart_money.heatmap.empty")}</p>
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
        {data.filing_delay_note || t("smart_money.heatmap.delay_note", { report_date: data.report_date ?? "-" })}
      </div>
      {viewMode === "sector" && dominantActions.length === 1 && (
        <div className="rounded-md border border-sky-500/30 bg-sky-500/10 p-3 text-xs text-sky-200">
          {t("smart_money.heatmap.uniform_action_hint", {
            action: t(`smart_money.action.${dominantActions[0]!.toLowerCase()}`),
          })}
        </div>
      )}

      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          aria-expanded={sopOpen}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("smart_money.heatmap.sop_title")}</span>
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", sopOpen && "rotate-180")} />
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("smart_money.heatmap.sop_content")}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={viewMode === "sector" ? "default" : "outline"}
          onClick={() => setViewMode("sector")}
        >
          {t("smart_money.heatmap.view_by_sector")}
        </Button>
        <Button
          size="sm"
          variant={viewMode === "guru" ? "default" : "outline"}
          onClick={() => setViewMode("guru")}
        >
          {t("smart_money.heatmap.view_by_guru")}
        </Button>
        <select
          value={sectorFilter}
          onChange={(event) => setSectorFilter(event.target.value)}
          aria-label={t("smart_money.heatmap.all_sectors")}
          className="h-9 min-h-[44px] rounded-md border border-input bg-background px-2 text-xs"
        >
          <option value="all">{t("smart_money.heatmap.all_sectors")}</option>
          {sectors.map((sector) => (
            <option key={sector} value={sector}>
              {sector}
            </option>
          ))}
        </select>
      </div>

      <div className="rounded-md border border-border p-2">
        {viewMode === "guru" && treeData.length === 0 ? (
          <p className="px-2 py-6 text-sm text-muted-foreground">{t("smart_money.heatmap.guru_view_empty")}</p>
        ) : (
          <ResponsiveContainer width="100%" height={420}>
            <Treemap data={treeData} dataKey="size" stroke="#111827" content={<HeatCell />}>
              <Tooltip content={<HeatmapTooltip t={t} />} />
            </Treemap>
          </ResponsiveContainer>
        )}
      </div>

      <div className="flex flex-wrap gap-4 text-xs">
        {Object.entries(ACTION_COLORS).map(([action, color]) => (
          <div key={action} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
            <span>{t(`smart_money.action.${action.toLowerCase()}`)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
