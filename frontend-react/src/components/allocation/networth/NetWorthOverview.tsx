import { Pie, PieChart, ResponsiveContainer, Tooltip, Cell } from "recharts"
import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { maskMoney } from "@/hooks/usePrivacyMode"
import type { NetWorthSummaryResponse } from "@/api/types/networth"

interface Props {
  summary?: NetWorthSummaryResponse | null
  privacyMode: boolean
}

const COLORS = ["#3b82f6", "#22c55e", "#ef4444"]

export function NetWorthOverview({ summary, privacyMode }: Props) {
  const { t } = useTranslation()
  if (!summary) return null

  const chartData = [
    {
      name: "investments",
      label: t("net_worth.segment_investments"),
      value: summary.investment_value,
    },
    {
      name: "other",
      label: t("net_worth.segment_assets"),
      value: summary.other_assets_value,
    },
    {
      name: "liabilities",
      label: t("net_worth.segment_liabilities"),
      value: summary.liabilities_value,
    },
  ].filter((x) => x.value > 0)

  return (
    <Card>
      <CardContent className="p-4 sm:p-6 space-y-4">
        <div>
          <p className="text-xs text-muted-foreground">{t("net_worth.overview_title")}</p>
          <p className="text-2xl font-bold tabular-nums">{maskMoney(summary.net_worth)}</p>
          {!privacyMode && (
            <p className="text-xs text-muted-foreground">
              {new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: summary.display_currency,
                minimumFractionDigits: 2,
              }).format(summary.net_worth)}
            </p>
          )}
          <p className="text-xs text-muted-foreground mt-1">{t("net_worth.summary_formula")}</p>
        </div>

        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={chartData} dataKey="value" nameKey="label" innerRadius={44} outerRadius={76}>
                {chartData.map((entry, idx) => (
                  <Cell key={entry.name} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number | string | undefined) => {
                  if (privacyMode) return "***"
                  const numeric = typeof value === "number" ? value : Number(value ?? 0)
                  return Number.isFinite(numeric) ? numeric.toFixed(2) : "0.00"
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
