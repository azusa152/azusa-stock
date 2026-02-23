import { useTranslation } from "react-i18next"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  LabelList,
  ResponsiveContainer,
} from "recharts"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import type { SectorBreakdownItem } from "@/api/types/smartMoney"

interface Props {
  data: SectorBreakdownItem[]
}

export function SectorChart({ data }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t("smart_money.overview.sector_empty")}</p>
    )
  }

  const sorted = [...data].sort((a, b) => b.weight_pct - a.weight_pct)
  const chartData = sorted.map((d) => ({ sector: d.sector, weight: d.weight_pct }))
  const height = Math.max(180, sorted.length * 28 + 60)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 4, right: 60, left: 8, bottom: 4 }}
      >
        <XAxis
          type="number"
          tick={{ fontSize: 9, fill: theme.tickColor }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
          label={{ value: t("smart_money.overview.sector_weight_axis"), position: "insideBottom", offset: -2, fontSize: 10, fill: theme.tickColor }}
        />
        <YAxis
          type="category"
          dataKey="sector"
          tick={{ fontSize: 10, fill: theme.tickColor }}
          axisLine={false}
          tickLine={false}
          width={110}
        />
        <Tooltip
          contentStyle={theme.tooltipStyle}
          formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("smart_money.overview.sector_weight_axis")]}
          labelStyle={{ color: theme.tooltipText }}
          cursor={{ fill: "rgba(128,128,128,0.08)" }}
        />
        <Bar dataKey="weight" fill="#3b82f6" radius={[0, 3, 3, 0]}>
          <LabelList
            dataKey="weight"
            position="right"
            formatter={(v: unknown) => typeof v === "number" ? `${v.toFixed(1)}%` : ""}
            style={{ fontSize: 9, fill: theme.tickColor }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
