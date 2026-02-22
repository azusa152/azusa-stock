import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Plot from "react-plotly.js"
import { useWithdraw } from "@/api/hooks/useAllocation"
import type { WithdrawResponse } from "@/api/types/allocation"
import { DISPLAY_CURRENCIES } from "@/lib/constants"

interface Props {
  privacyMode: boolean
}

function fmtCurrency(v: number, currency: string, privacyMode: boolean): string {
  if (privacyMode) return "***"
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(v)
}

export function SmartWithdrawal({ privacyMode }: Props) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [notify, setNotify] = useState(false)
  const [result, setResult] = useState<WithdrawResponse | null>(null)

  const withdrawMutation = useWithdraw()

  const handleCalculate = () => {
    if (!amount.trim() || isNaN(Number(amount)) || Number(amount) <= 0) return
    withdrawMutation.mutate(
      { amount: Number(amount), currency, notify },
      {
        onSuccess: (data) => setResult(data),
      },
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold">{t("allocation.withdraw.title")}</p>

      {/* Input form */}
      <div className="space-y-3 max-w-sm">
        <div className="space-y-1">
          <label className="text-xs font-medium">{t("allocation.withdraw.amount_label")}</label>
          <Input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            type="number"
            placeholder="e.g. 10000"
            className="text-sm"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium">{t("allocation.withdraw.currency_label")}</label>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
          >
            {DISPLAY_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={notify}
            onChange={(e) => setNotify(e.target.checked)}
            className="rounded"
          />
          {t("allocation.withdraw.notify_label")}
        </label>
        <Button
          onClick={handleCalculate}
          disabled={withdrawMutation.isPending || !amount.trim()}
          size="sm"
        >
          {withdrawMutation.isPending ? t("common.loading") : t("allocation.withdraw.calculate_button")}
        </Button>
        {withdrawMutation.isError && (
          <p className="text-xs text-destructive">{t("common.error")}</p>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4 mt-2">
          {/* Summary */}
          <div className="rounded-md border border-border p-3 text-sm space-y-1">
            <p className="font-semibold">{result.message}</p>
            <div className="grid grid-cols-3 gap-3 text-xs mt-2">
              <div>
                <p className="text-muted-foreground">{t("allocation.withdraw.target")}</p>
                <p className="font-semibold">{fmtCurrency(result.target_amount, currency, privacyMode)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">{t("allocation.withdraw.total_sell")}</p>
                <p className="font-semibold">{fmtCurrency(result.total_sell_value, currency, privacyMode)}</p>
              </div>
              {result.shortfall > 0 && (
                <div>
                  <p className="text-muted-foreground">{t("allocation.withdraw.shortfall")}</p>
                  <p className="font-semibold text-red-500">{fmtCurrency(result.shortfall, currency, privacyMode)}</p>
                </div>
              )}
            </div>
          </div>

          {/* Sell recommendations table */}
          {result.recommendations.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
                    <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
                    <th className="text-right py-0.5 pr-2">{t("allocation.withdraw.col_qty")}</th>
                    <th className="text-right py-0.5 pr-2">{t("allocation.withdraw.col_value")}</th>
                    <th className="text-left py-0.5">{t("allocation.withdraw.col_reason")}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recommendations.map((r, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-0.5 pr-2 font-medium">{r.ticker}</td>
                      <td className="py-0.5 pr-2 text-muted-foreground">{r.category}</td>
                      <td className="py-0.5 pr-2 text-right">{privacyMode ? "***" : r.quantity_to_sell.toFixed(2)}</td>
                      <td className="py-0.5 pr-2 text-right">{fmtCurrency(r.sell_value, currency, privacyMode)}</td>
                      <td className="py-0.5 text-muted-foreground">{r.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Post-sell drift mini pie */}
          {Object.keys(result.post_sell_drifts).length > 0 && (
            <div>
              <p className="text-xs font-semibold mb-1">{t("allocation.withdraw.post_drift_title")}</p>
              <Plot
                data={[{
                  type: "pie",
                  labels: Object.keys(result.post_sell_drifts),
                  values: Object.values(result.post_sell_drifts).map((d) => d.current_pct),
                  hole: 0.3,
                  textinfo: "label+percent",
                }]}
                layout={{
                  height: 200,
                  margin: { l: 0, r: 0, t: 5, b: 0 },
                  showlegend: false,
                  plot_bgcolor: "rgba(0,0,0,0)",
                  paper_bgcolor: "rgba(0,0,0,0)",
                  font: { size: 10 },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: "100%" }}
                useResizeHandler
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
