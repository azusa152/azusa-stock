import { useTranslation } from "react-i18next"
import type { TFunction } from "i18next"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  CATEGORY_ICON_SHORT,
  SCAN_SIGNAL_ICONS,
  BUY_OPPORTUNITY_SIGNALS,
  RISK_WARNING_SIGNALS,
} from "@/lib/constants"
import type { Stock, EnrichedStock, RebalanceResponse, SignalActivityItem } from "@/api/types/dashboard"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function formatDuration(t: TFunction<any>, days: number): string {
  if (days < 7) return t("dashboard.signal_duration_days", { count: days })
  if (days < 30) return t("dashboard.signal_duration_weeks", { count: Math.floor(days / 7) })
  return t("dashboard.signal_duration_months", { count: Math.floor(days / 30) })
}

interface SignalRowProps {
  stock: Stock
  signal: string
  activity?: SignalActivityItem
}

function SignalRow({ stock, signal, activity }: SignalRowProps) {
  const { t } = useTranslation()
  const icon = SCAN_SIGNAL_ICONS[signal] ?? "➖"
  const catIcon = CATEGORY_ICON_SHORT[stock.category] ?? ""
  const signalKey = signal.toLowerCase()
  const signalLabel = t(`config.signal.${signalKey}`, { defaultValue: signal })

  const isNew = activity?.is_new ?? false
  const durationDays = activity?.duration_days
  const previousSignal = activity?.previous_signal
  const consecutiveScans = activity?.consecutive_scans ?? 1

  const durationBadge = isNew
    ? t("dashboard.signal_new")
    : durationDays != null
      ? formatDuration(t, durationDays)
      : null

  const previousSignalLabel = previousSignal
    ? t(`config.signal.${previousSignal.toLowerCase()}`, { defaultValue: previousSignal })
    : null

  return (
    <div className="py-1.5">
      <div className="grid grid-cols-[1.5rem_5rem_auto_auto] gap-2 items-center">
        <span>{icon}</span>
        <span className="font-semibold text-sm">{stock.ticker}</span>
        <span className="text-xs text-muted-foreground">
          {catIcon} {stock.category}
        </span>
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{signalLabel}</span>
          {durationBadge && (
            <span
              className={
                isNew
                  ? "text-xs font-semibold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 animate-pulse"
                  : "text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
              }
            >
              {durationBadge}
            </span>
          )}
        </div>
      </div>
      {(previousSignalLabel || consecutiveScans > 1) && (
        <div className="flex items-center gap-2 pl-7 mt-0.5">
          {previousSignalLabel && (
            <span className="text-xs text-muted-foreground">
              {t("dashboard.signal_was", { signal: previousSignalLabel })}
            </span>
          )}
          {consecutiveScans > 1 && (
            <span className="text-xs text-muted-foreground/70">
              · {t("dashboard.signal_consecutive", { count: consecutiveScans })}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

interface Props {
  stocks?: Stock[]
  enrichedStocks?: EnrichedStock[]
  rebalance?: RebalanceResponse | null
  signalActivity?: SignalActivityItem[]
}

export function SignalAlerts({ stocks = [], enrichedStocks = [], rebalance, signalActivity = [] }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const enrichedSignalMap: Record<string, string> = {}
  for (const es of enrichedStocks) {
    if (es.ticker) {
      enrichedSignalMap[es.ticker] = es.computed_signal ?? es.last_scan_signal ?? "NORMAL"
    }
  }

  const activityMap: Record<string, SignalActivityItem> = {}
  for (const item of signalActivity) {
    activityMap[item.ticker] = item
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
                  <SignalRow
                    key={s.ticker}
                    stock={s}
                    signal={resolveSignal(s)}
                    activity={activityMap[s.ticker]}
                  />
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
                  <SignalRow
                    key={s.ticker}
                    stock={s}
                    signal={resolveSignal(s)}
                    activity={activityMap[s.ticker]}
                  />
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
