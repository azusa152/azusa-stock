import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { CATEGORY_ICON_SHORT } from "@/lib/constants"
import type { RebalanceResponse, HoldingDetail } from "@/api/types/dashboard"

const TOP_LIMIT = 10

interface Props {
  rebalance?: RebalanceResponse | null
}

function ChangeCell({ value }: { value?: number | null }) {
  if (value == null) return <td className="text-right px-3 py-2 text-sm">N/A</td>
  const isPos = value >= 0
  return (
    <td className={`text-right px-3 py-2 text-sm font-medium ${isPos ? "text-green-500" : "text-red-500"}`}>
      {isPos ? "▲" : "▼"}{Math.abs(value).toFixed(2)}%
    </td>
  )
}

function ReturnCells({ holding, isPrivate }: { holding: HoldingDetail; isPrivate: boolean }) {
  const { cost_total, market_value } = holding
  if (!cost_total || cost_total <= 0) {
    return (
      <>
        <td className="text-right px-3 py-2 text-sm text-muted-foreground">—</td>
        <td className="text-right px-3 py-2 text-sm text-muted-foreground">—</td>
      </>
    )
  }
  const gainLoss = market_value - cost_total
  const returnPct = (gainLoss / cost_total) * 100
  const isPos = returnPct >= 0
  const colorClass = isPos ? "text-green-500" : "text-red-500"
  return (
    <>
      <td className={`text-right px-3 py-2 text-sm font-medium ${colorClass}`}>
        {isPos ? "▲" : "▼"}{Math.abs(returnPct).toFixed(1)}%
      </td>
      <td className={`text-right px-3 py-2 text-sm ${colorClass}`}>
        {isPrivate ? "***" : `${isPos ? "+" : "-"}$${Math.abs(gainLoss).toLocaleString("en-US", { maximumFractionDigits: 0 })}`}
      </td>
    </>
  )
}

export function TopHoldings({ rebalance }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  if (!rebalance?.holdings_detail?.length) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">{t("dashboard.no_holdings_data")}</p>
          <Button size="sm" variant="outline" className="mt-3" onClick={() => navigate("/allocation")}>
            {t("dashboard.button_add_holdings")}
          </Button>
        </CardContent>
      </Card>
    )
  }

  const sorted = [...rebalance.holdings_detail].sort((a, b) => b.weight_pct - a.weight_pct)
  const top = sorted.slice(0, TOP_LIMIT)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {t("dashboard.top_holdings_title", { limit: TOP_LIMIT })}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-xs text-muted-foreground">
                <th className="text-left px-3 py-2">{t("dashboard.holdings_table.ticker")}</th>
                <th className="text-left px-3 py-2">{t("dashboard.holdings_table.category")}</th>
                <th className="text-right px-3 py-2">{t("dashboard.holdings_table.weight")}</th>
                <th className="text-right px-3 py-2">{t("dashboard.holdings_table.market_value")}</th>
                <th className="text-right px-3 py-2">{t("dashboard.holdings_table.daily_change")}</th>
                <th className="text-right px-3 py-2">{t("dashboard.holdings_table.total_return")}</th>
                <th className="text-right px-3 py-2">{t("dashboard.holdings_table.gain_loss")}</th>
              </tr>
            </thead>
            <tbody>
              {top.map((h) => (
                <tr key={`${h.ticker}-${h.weight_pct}`} className="border-t border-border/50 hover:bg-muted/30">
                  <td className="px-3 py-2 font-semibold">{h.ticker}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {CATEGORY_ICON_SHORT[h.category] ?? ""} {h.category}
                  </td>
                  <td className="text-right px-3 py-2">{h.weight_pct.toFixed(1)}%</td>
                  <td className="text-right px-3 py-2">
                    {isPrivate ? "***" : `$${h.market_value.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
                  </td>
                  <ChangeCell value={h.change_pct} />
                  <ReturnCells holding={h} isPrivate={isPrivate} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
