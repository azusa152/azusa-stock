import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ReferenceLine,
  LabelList,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  CATEGORY_ICON_SHORT,
  CATEGORY_COLOR_MAP,
  CATEGORY_COLOR_FALLBACK,
} from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import type { RebalanceResponse, ProfileResponse } from "@/api/types/dashboard"

interface Props {
  rebalance?: RebalanceResponse | null
  profile?: ProfileResponse | null
  isLoading?: boolean
}

export function AllocationGlance({ rebalance, profile, isLoading = false }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-[200px] w-full" />
          <Skeleton className="h-[200px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!rebalance || !profile || !rebalance.categories) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">{t("dashboard.no_allocation_data")}</p>
          <div className="flex gap-2 mt-3">
            <Button size="sm" variant="outline" onClick={() => navigate("/allocation")}>
              {t("dashboard.button_setup_persona")}
            </Button>
            <Button size="sm" variant="outline" onClick={() => navigate("/radar")}>
              {t("dashboard.button_track_stock")}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const targetConfig = profile.config
  const breakdown = rebalance.categories

  const catKeys = Object.keys(targetConfig)

  const pieData = catKeys.map((k) => ({
    name: `${CATEGORY_ICON_SHORT[k] ?? ""} ${k}`,
    target: targetConfig[k] ?? 0,
    actual: breakdown[k]?.current_pct ?? 0,
    color: CATEGORY_COLOR_MAP[k] ?? CATEGORY_COLOR_FALLBACK,
  }))

  const driftData = catKeys.map((k) => ({
    name: `${CATEGORY_ICON_SHORT[k] ?? ""} ${k}`,
    drift: breakdown[k]?.drift_pct ?? 0,
    fill: Math.abs(breakdown[k]?.drift_pct ?? 0) > 5 ? "#ef4444" : "#9ca3af",
  }))

  const tooltipStyle = theme.tooltipStyle

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("dashboard.allocation_title")}</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dual donut side by side */}
        <div className="space-y-1">
          <div className="grid grid-cols-2 gap-1">
            <div>
              <p className="text-xs text-center text-muted-foreground mb-1">{t("dashboard.chart.target")}</p>
              <ResponsiveContainer width="100%" height={130}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="target"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius="50%"
                    outerRadius="80%"
                    paddingAngle={1}
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("dashboard.chart.target_pct")]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="text-xs text-center text-muted-foreground mb-1">{t("dashboard.chart.actual")}</p>
              <ResponsiveContainer width="100%" height={130}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="actual"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius="50%"
                    outerRadius="80%"
                    paddingAngle={1}
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`, t("dashboard.chart.actual_pct")]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Legend */}
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
            {pieData.map((entry) => (
              <span key={entry.name} className="flex items-center gap-1 text-xs text-muted-foreground">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
                {entry.name}
              </span>
            ))}
          </div>
        </div>

        {/* Drift bar chart */}
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("dashboard.drift_title")}</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={driftData} margin={{ top: 14, right: 8, left: -16, bottom: 0 }}>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9, fill: theme.tickColor }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 9, fill: theme.tickColor }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
                width={36}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v: number | undefined) => [`${v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}` : ""}%`, t("dashboard.chart.drift_yaxis")]}
                labelStyle={{ color: theme.tooltipText }}
                cursor={{ fill: "rgba(128,128,128,0.08)" }}
              />
              <ReferenceLine y={5} stroke="#f97316" strokeDasharray="3 3" strokeWidth={1} />
              <ReferenceLine y={-5} stroke="#f97316" strokeDasharray="3 3" strokeWidth={1} />
              <Bar dataKey="drift" radius={[3, 3, 0, 0]}>
                {driftData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
                <LabelList
                  dataKey="drift"
                  position="top"
                  formatter={(v: unknown) => typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%` : ""}
                  style={{ fontSize: 9, fill: theme.tickColor }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
