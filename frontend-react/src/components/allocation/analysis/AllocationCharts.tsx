import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Treemap,
  ResponsiveContainer,
} from "recharts"
import type { CategoryAllocation } from "@/api/types/allocation"
import { CATEGORY_COLOR_MAP, CATEGORY_COLOR_FALLBACK } from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"

interface Props {
  categories: Record<string, CategoryAllocation>
}

function getCategoryColor(name: string): string {
  return CATEGORY_COLOR_MAP[name] ?? CATEGORY_COLOR_FALLBACK
}

interface TreemapContentProps {
  x?: number; y?: number; width?: number; height?: number
  name?: string; value?: number; fill?: string
  payload?: { fill?: string }
}

function TreemapContent({ x = 0, y = 0, width = 0, height = 0, name, value, fill, payload }: TreemapContentProps) {
  const cellFill = fill || payload?.fill || "#6b7280"
  if (width < 30 || height < 20) return null
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={cellFill} rx={3} />
      {width > 50 && height > 28 && (
        <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle" fill="#fff" fontSize={11} fontWeight={500}>
          {name}
        </text>
      )}
      {width > 50 && height > 28 && (
        <text x={x + width / 2} y={y + height / 2 + 8} textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize={9}>
          {typeof value === "number" ? `${value.toFixed(1)}%` : ""}
        </text>
      )}
    </g>
  )
}

export function AllocationCharts({ categories }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const [chartType, setChartType] = useState<"pie" | "treemap">("pie")

  const entries = Object.entries(categories)
  const pieData = entries.map(([name, v]) => ({
    name,
    target: v.target_pct,
    actual: v.current_pct,
    color: getCategoryColor(name),
  }))

  const treemapTargetData = entries.map(([name, v]) => ({
    name,
    size: v.target_pct,
    fill: getCategoryColor(name),
  }))
  const treemapActualData = entries.map(([name, v]) => ({
    name,
    size: v.current_pct,
    fill: getCategoryColor(name),
  }))

  const tooltipStyle = theme.tooltipStyle

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{t("allocation.charts.title")}</p>
        <div className="flex gap-1">
          <button
            onClick={() => setChartType("pie")}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${
              chartType === "pie" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-muted/30"
            }`}
          >
            {t("allocation.charts.toggle_pie")}
          </button>
          <button
            onClick={() => setChartType("treemap")}
            className={`text-xs px-2 py-0.5 rounded border transition-colors ${
              chartType === "treemap" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-muted/30"
            }`}
          >
            {t("allocation.charts.toggle_treemap")}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {/* Target */}
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.charts.target")}</p>
          {chartType === "pie" ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="target"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius="35%"
                  outerRadius="70%"
                  paddingAngle={1}
                  label={({ name: n, value: v }) => `${n} ${(v as number).toFixed(1)}%`}
                  labelLine={false}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("allocation.charts.target")]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <Treemap
                data={treemapTargetData}
                dataKey="size"
                content={<TreemapContent />}
              >
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("allocation.charts.target")]}
                />
              </Treemap>
            </ResponsiveContainer>
          )}
        </div>

        {/* Actual */}
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.charts.actual")}</p>
          {chartType === "pie" ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="actual"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius="35%"
                  outerRadius="70%"
                  paddingAngle={1}
                  label={({ name: n, value: v }) => `${n} ${(v as number).toFixed(1)}%`}
                  labelLine={false}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("allocation.charts.actual")]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <Treemap
                data={treemapActualData}
                dataKey="size"
                content={<TreemapContent />}
              >
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("allocation.charts.actual")]}
                />
              </Treemap>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
