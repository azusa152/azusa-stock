import { useTranslation } from "react-i18next"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts"
import type { CategoryAllocation } from "@/api/types/allocation"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"

interface Props {
  categories: Record<string, CategoryAllocation>
}

export function DriftChart({ categories }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  const chartData = Object.entries(categories)
    .sort((a, b) => b[1].drift_pct - a[1].drift_pct)
    .map(([name, v]) => ({
      name,
      drift: v.drift_pct,
      fill: v.drift_pct > 0 ? "#ef4444" : "#22c55e",
    }))

  const height = Math.max(160, chartData.length * 32 + 60)

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.drift.title")}</p>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 20 }}>
          <XAxis
            type="number"
            tick={{ fontSize: 9, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
            label={{ value: t("allocation.drift.axis_label"), position: "insideBottom", offset: -10, fontSize: 10, fill: theme.tickColor }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 10, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
            width={90}
          />
          <Tooltip
            contentStyle={theme.tooltipStyle}
            formatter={(v: number | undefined) => [`${v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}` : ""}%`, t("allocation.drift.axis_label")]}
            labelStyle={{ color: theme.tooltipText }}
            cursor={{ fill: "rgba(128,128,128,0.08)" }}
          />
          <ReferenceLine x={5} stroke="#f59e0b" strokeDasharray="3 3" strokeWidth={1} />
          <ReferenceLine x={-5} stroke="#f59e0b" strokeDasharray="3 3" strokeWidth={1} />
          <ReferenceLine x={10} stroke="#f97316" strokeDasharray="4 2" strokeWidth={1} />
          <ReferenceLine x={-10} stroke="#f97316" strokeDasharray="4 2" strokeWidth={1} />
          <Bar dataKey="drift" radius={[0, 3, 3, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
            <LabelList
              dataKey="drift"
              position="right"
              formatter={(v: unknown) => typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` : ""}
              style={{ fontSize: 9, fill: theme.tickColor }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span>
          <span className="inline-block w-3 h-px bg-yellow-500 mr-1 align-middle" />
          {t("allocation.drift.threshold_5")}
        </span>
        <span>
          <span className="inline-block w-3 h-px bg-orange-500 mr-1 align-middle" />
          {t("allocation.drift.threshold_10")}
        </span>
      </div>
    </div>
  )
}
