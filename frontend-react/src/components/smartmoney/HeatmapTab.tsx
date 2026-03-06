import { useMemo, useState } from "react"
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

type ViewMode = "sector" | "guru"

type HeatCellProps = {
  x?: number
  y?: number
  width?: number
  height?: number
  name?: string
  fill?: string
}

function HeatCell({ x = 0, y = 0, width = 0, height = 0, name = "", fill = "#64748b" }: HeatCellProps) {
  if (width < 40 || height < 28) {
    return <rect x={x} y={y} width={width} height={height} fill={fill} stroke="rgba(255,255,255,0.1)" />
  }
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="rgba(255,255,255,0.1)" />
      <text x={x + 6} y={y + 16} fill="#fff" fontSize={11} fontWeight={600}>
        {name}
      </text>
    </g>
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

  const treeData = useMemo(() => {
    if (viewMode === "guru") {
      const byGuru: Record<string, Array<{ name: string; size: number; fill: string }>> = {}
      for (const item of filteredItems) {
        for (const guru of item.gurus ?? []) {
          const guruName = guru.guru_display_name
          byGuru[guruName] ??= []
          byGuru[guruName].push({
            name: item.ticker,
            size: Math.max(guru.weight_pct ?? 0.001, 0.001),
            fill: ACTION_COLORS[guru.action] ?? ACTION_COLORS.UNCHANGED,
          })
        }
      }
      return Object.entries(byGuru).map(([name, children]) => ({ name, children }))
    }

    const bySector: Record<string, Array<{ name: string; size: number; fill: string }>> = {}
    for (const item of filteredItems) {
      const sector = item.sector ?? "Unknown"
      bySector[sector] ??= []
      bySector[sector].push({
        name: item.ticker,
        size: Math.max(item.combined_weight_pct ?? 0.001, 0.001),
        fill: ACTION_COLORS[item.dominant_action] ?? ACTION_COLORS.UNCHANGED,
      })
    }
    return Object.entries(bySector).map(([name, children]) => ({ name, children }))
  }, [filteredItems, viewMode])

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

      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          aria-expanded={sopOpen}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("smart_money.heatmap.sop_title")}</span>
          <span className="text-muted-foreground text-xs">{sopOpen ? "▲" : "▼"}</span>
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
        <ResponsiveContainer width="100%" height={420}>
          <Treemap data={treeData} dataKey="size" stroke="#111827" content={<HeatCell />}>
            <Tooltip
              contentStyle={{ background: "rgba(17,24,39,0.96)", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </Treemap>
        </ResponsiveContainer>
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
