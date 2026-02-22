import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  CATEGORY_ICON_SHORT,
  SCAN_SIGNAL_ICONS,
  BUY_OPPORTUNITY_SIGNALS,
  RISK_WARNING_SIGNALS,
} from "@/lib/constants"
import type { Stock, EnrichedStock, RebalanceResponse } from "@/api/types/dashboard"

interface SignalRowProps {
  stock: Stock
  signal: string
}

function SignalRow({ stock, signal }: SignalRowProps) {
  const icon = SCAN_SIGNAL_ICONS[signal] ?? "⚪"
  const catIcon = CATEGORY_ICON_SHORT[stock.category] ?? ""

  return (
    <div className="grid grid-cols-[1.5rem_5rem_auto_auto] gap-2 items-center py-1">
      <span>{icon}</span>
      <span className="font-semibold text-sm">{stock.ticker}</span>
      <span className="text-xs text-muted-foreground">
        {catIcon} {stock.category}
      </span>
      <span className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded ml-auto">
        {signal}
      </span>
    </div>
  )
}

interface Props {
  stocks?: Stock[]
  enrichedStocks?: EnrichedStock[]
  rebalance?: RebalanceResponse | null
}

export function SignalAlerts({ stocks = [], enrichedStocks = [], rebalance }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const enrichedSignalMap: Record<string, string> = {}
  for (const es of enrichedStocks) {
    if (es.ticker) {
      enrichedSignalMap[es.ticker] = es.computed_signal ?? es.last_scan_signal ?? "NORMAL"
    }
  }

  function resolveSignal(stock: Stock): string {
    return enrichedSignalMap[stock.ticker] ?? stock.last_scan_signal ?? "NORMAL"
  }

  const activeStocks = stocks.filter((s) => s.is_active)
  const buyStocks = activeStocks.filter((s) => BUY_OPPORTUNITY_SIGNALS.has(resolveSignal(s)))
  const riskStocks = activeStocks.filter((s) => RISK_WARNING_SIGNALS.has(resolveSignal(s)))

  const advice = rebalance?.advice ?? []

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t("dashboard.signal_alerts_title")}</CardTitle>
          {activeStocks.length === 0 && (
            <Button size="sm" variant="outline" onClick={() => navigate("/radar")}>
              {t("dashboard.button_goto_radar")}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {activeStocks.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.no_tracking_stocks")}</p>
        ) : buyStocks.length === 0 && riskStocks.length === 0 ? (
          <div className="flex items-center gap-2 rounded-md bg-green-500/10 text-green-700 dark:text-green-400 px-3 py-2 text-sm">
            {t("dashboard.all_signals_normal")}
          </div>
        ) : (
          <div className="space-y-3">
            {buyStocks.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  {t("dashboard.signal_buy_title")}
                </p>
                {buyStocks.map((s) => (
                  <SignalRow key={s.ticker} stock={s} signal={resolveSignal(s)} />
                ))}
              </div>
            )}

            {buyStocks.length > 0 && riskStocks.length > 0 && (
              <hr className="border-border" />
            )}

            {riskStocks.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  {t("dashboard.signal_risk_title")}
                </p>
                {riskStocks.map((s) => (
                  <SignalRow key={s.ticker} stock={s} signal={resolveSignal(s)} />
                ))}

                {advice.length > 0 && (
                  <>
                    <hr className="border-border my-2" />
                    <p className="text-xs font-medium text-muted-foreground mb-1">
                      {t("dashboard.rebalance_advice_title")}
                    </p>
                    {advice.slice(0, 5).map((item, i) => (
                      <p key={i} className="text-xs text-muted-foreground py-0.5">
                        • {item}
                      </p>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
