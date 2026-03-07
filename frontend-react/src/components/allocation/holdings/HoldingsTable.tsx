import { useTranslation } from "react-i18next"
import type { HoldingDetail } from "@/api/types/allocation"
import { FINANCE_TEXT } from "@/lib/colors"

interface Props {
  holdings: HoldingDetail[]
  privacyMode: boolean
}

function fmt(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—"
  return v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function fmtMasked(v: number | null | undefined, privacyMode: boolean, decimals = 0): string {
  if (privacyMode) return "***"
  return fmt(v, decimals)
}

function fmtQuantity(ticker: string, category: string, quantity: number, privacyMode: boolean): string {
  if (privacyMode) return "***"
  if (category !== "Crypto") return fmt(quantity, 2)
  const max = ticker.startsWith("BTC") ? 8 : ticker.startsWith("ETH") ? 6 : 4
  return quantity.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: max,
  })
}

function fmtPct(v: number, showSign = true): string {
  const sign = showSign && v >= 0 ? "+" : ""
  return `${sign}${v.toFixed(2)}%`
}

/** Compute FX return % given purchase and current FX rate */
function computeFxReturn(purchaseFx: number | null | undefined, currentFx: number | null | undefined): number | null {
  if (purchaseFx == null || currentFx == null || purchaseFx === 0) return null
  return (currentFx / purchaseFx - 1) * 100
}

export function HoldingsTable({ holdings, privacyMode }: Props) {
  const { t } = useTranslation()

  if (!holdings || holdings.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("allocation.holdings.empty")}</p>
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.holdings.title")}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.qty")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.value")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.weight_pct")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.cost")}</th>
              <th className="text-right py-0.5">{t("allocation.col.change_pct")}</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h, i) => {
              const isCrypto = h.category === "Crypto"
              const fxReturn = computeFxReturn(h.purchase_fx_rate, h.current_fx_rate)
              const showFxBreakdown = h.purchase_fx_rate != null && fxReturn != null && h.currency !== "USD"

              // Home return = local price return + FX impact (approximate additive)
              const homeReturn =
                showFxBreakdown && h.change_pct != null
                  ? h.change_pct + fxReturn
                  : null

              return (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.category}</td>
                  <td className="py-0.5 pr-2 text-right">{fmtQuantity(h.ticker, h.category, h.quantity, privacyMode)}</td>
                  <td className="py-0.5 pr-2 text-right">{fmtMasked(h.market_value, privacyMode)}</td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
                  </td>
                  <td className="py-0.5 pr-2 text-right">{fmtMasked(h.cost_total, privacyMode)}</td>
                  <td className="py-0.5 text-right">
                    <div
                      className={h.change_pct != null ? (h.change_pct >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss) : undefined}
                    >
                      {h.change_pct != null ? `${fmtPct(h.change_pct)}${isCrypto ? ` (${t("allocation.crypto.change_24h_short")})` : ""}` : "—"}
                    </div>
                    {isCrypto && h.change_pct != null && Math.abs(h.change_pct) >= 5 && (
                      <div className={`text-[10px] leading-tight mt-0.5 ${FINANCE_TEXT.warning}`}>
                        {t("allocation.crypto.volatility_warning")}
                      </div>
                    )}
                    {showFxBreakdown && (
                      <div className="text-muted-foreground text-[10px] leading-tight mt-0.5">
                        {homeReturn != null && (
                          <div className={homeReturn >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}>
                            {t("allocation.col.home_return", { pct: fmtPct(homeReturn) })}
                          </div>
                        )}
                        <div className={fxReturn >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}>
                          {t("allocation.col.fx_return", { pct: fmtPct(fxReturn) })}
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
