import { useTranslation } from "react-i18next"
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, LabelList, ResponsiveContainer } from "recharts"
import { Skeleton } from "@/components/ui/skeleton"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { useGrandPortfolio } from "@/api/hooks/useSmartMoney"
import { SectorChart } from "./SectorChart"
import { ActionBadge } from "./ActionBadge"
import { formatValue, ACTION_COLORS } from "./formatters"

export function GrandPortfolioTab({ style }: { style?: string | null }) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const { data, isLoading } = useGrandPortfolio(style)

  if (isLoading) return <Skeleton className="h-64 w-full" />
  if (!data || data.items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("smart_money.grand_portfolio.no_data")}
      </p>
    )
  }

  const top20 = data.items.slice(0, 20)

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-md border p-3">
          <p className="text-muted-foreground">{t("smart_money.grand_portfolio.total_aum")}</p>
          <p className="font-bold text-base">{formatValue(data.total_value)}</p>
        </div>
        <div className="rounded-md border p-3">
          <p className="text-muted-foreground">{t("smart_money.grand_portfolio.unique_tickers")}</p>
          <p className="font-bold text-base">{data.unique_tickers}</p>
        </div>
      </div>

      {/* Top-20 bar chart */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.grand_portfolio.top20_header")}</p>
        <ResponsiveContainer width="100%" height={Math.max(220, top20.length * 22 + 60)}>
          <BarChart
            data={top20.map((item) => ({
              name: item.ticker,
              weight: item.combined_weight_pct,
              fill: ACTION_COLORS[item.dominant_action as keyof typeof ACTION_COLORS] ?? ACTION_COLORS.UNCHANGED,
            }))}
            layout="vertical"
            margin={{ top: 4, right: 56, left: 8, bottom: 20 }}
          >
            <XAxis
              type="number"
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 9, fill: theme.tickColor }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 9, fill: theme.tickColor }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
            <Tooltip
              contentStyle={theme.tooltipStyle}
              formatter={(v) => {
                const n = typeof v === "number" ? v : 0
                return [`${n.toFixed(2)}%`, t("smart_money.grand_portfolio.combined_weight")]
              }}
              labelStyle={{ color: theme.tooltipText }}
              cursor={{ fill: "rgba(128,128,128,0.08)" }}
            />
            <Bar dataKey="weight" radius={[0, 3, 3, 0]}>
              {top20.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    ACTION_COLORS[entry.dominant_action as keyof typeof ACTION_COLORS] ??
                    ACTION_COLORS.UNCHANGED
                  }
                />
              ))}
              <LabelList
                dataKey="weight"
                position="right"
                formatter={(v) => {
                  const n = typeof v === "number" ? v : 0
                  return `${n.toFixed(1)}%`
                }}
                style={{ fontSize: 9, fill: theme.tickColor }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      {/* Sector chart */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.overview.sector_header")}</p>
        <SectorChart data={data.sector_breakdown} />
      </section>

      {/* Full holdings table */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.grand_portfolio.table_header")}</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground border-b border-border">
                <th className="text-left py-0.5 pr-2">#</th>
                <th className="text-left py-0.5 pr-2">{t("smart_money.col.ticker")}</th>
                <th className="text-left py-0.5 pr-2">{t("smart_money.col.company")}</th>
                <th className="text-right py-0.5 pr-2">{t("smart_money.grand_portfolio.combined_weight")}</th>
                <th className="text-right py-0.5 pr-2">{t("smart_money.col.value")}</th>
                <th className="text-left py-0.5 pr-2">{t("smart_money.col.sector")}</th>
                <th className="text-left py-0.5 pr-2">{t("smart_money.overview.consensus_gurus")}</th>
                <th className="text-left py-0.5">{t("smart_money.col.action")}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-0.5 pr-2 text-muted-foreground">{i + 1}</td>
                  <td className="py-0.5 pr-2 font-medium">{item.ticker ?? "—"}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground max-w-[140px] truncate">
                    {item.company_name}
                  </td>
                  <td className="py-0.5 pr-2 text-right">{item.combined_weight_pct.toFixed(2)}%</td>
                  <td className="py-0.5 pr-2 text-right">{formatValue(item.total_value)}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{item.sector ?? "—"}</td>
                  <td className="py-0.5 pr-2">{item.guru_count}</td>
                  <td className="py-0.5">
                    <ActionBadge action={item.dominant_action} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
