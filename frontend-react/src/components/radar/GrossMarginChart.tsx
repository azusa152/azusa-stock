import { useTranslation } from "react-i18next"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  LabelList,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import type { MoatAnalysis } from "@/api/hooks/useRadar"

interface Props {
  data: MoatAnalysis
}

const MOAT_STATUS_COLOR: Record<string, string> = {
  HEALTHY: "text-green-600 dark:text-green-400",
  DETERIORATING: "text-red-600 dark:text-red-400",
  STABLE: "text-yellow-600 dark:text-yellow-400",
  NOT_AVAILABLE: "text-muted-foreground",
}

export function GrossMarginChart({ data }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  const trend = data.margin_trend?.filter((p) => p.value != null) ?? []

  if (trend.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground">{t("radar.stock_card.moat_chart_title")}</p>
        <p className="text-xs text-muted-foreground">{t("chart.insufficient_data")}</p>
      </div>
    )
  }

  const chartData = trend.map((p, i) => ({
    date: p.date,
    value: p.value as number,
    fill: i === 0 ? "#6b7280" : ((p.value as number) >= (trend[i - 1].value as number) ? "#22c55e" : "#ef4444"),
  }))

  const moatColor = MOAT_STATUS_COLOR[data.moat] ?? "text-muted-foreground"

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{t("radar.stock_card.moat_chart_title")}</p>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={chartData} margin={{ top: 18, right: 8, left: -16, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 9, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 9, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
            width={42}
          />
          <Tooltip
            contentStyle={theme.tooltipStyle}
            formatter={(value: number | undefined) => value != null ? [`${value.toFixed(1)}%`, t("chart.gross_margin")] : ["", ""]}
            labelStyle={{ color: theme.tooltipText }}
            cursor={{ fill: "rgba(128,128,128,0.08)" }}
          />
          {trend.length >= 2 && (
            <ReferenceLine
              y={trend[trend.length - 2].value as number}
              stroke="#6b7280"
              strokeDasharray="3 3"
              strokeWidth={1}
            />
          )}
          <Bar dataKey="value" radius={[3, 3, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
            <LabelList
              dataKey="value"
              position="top"
              formatter={(v: unknown) => typeof v === "number" ? `${v.toFixed(1)}%` : ""}
              style={{ fontSize: 9, fill: theme.tickColor }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {data.details && (
        <p className={`text-xs ${moatColor}`}>{data.details}</p>
      )}
    </div>
  )
}
