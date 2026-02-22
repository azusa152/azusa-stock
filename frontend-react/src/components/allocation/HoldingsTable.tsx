import { useTranslation } from "react-i18next"
import type { HoldingDetail } from "@/api/types/allocation"

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
            {holdings.map((h, i) => (
              <tr key={i} className="border-b border-border/50">
                <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                <td className="py-0.5 pr-2 text-muted-foreground">{h.category}</td>
                <td className="py-0.5 pr-2 text-right">{fmtMasked(h.quantity, privacyMode, 2)}</td>
                <td className="py-0.5 pr-2 text-right">{fmtMasked(h.market_value, privacyMode)}</td>
                <td className="py-0.5 pr-2 text-right">
                  {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
                </td>
                <td className="py-0.5 pr-2 text-right">{fmtMasked(h.cost_total, privacyMode)}</td>
                <td
                  className="py-0.5 text-right"
                  style={{ color: h.change_pct != null ? (h.change_pct >= 0 ? "#22c55e" : "#ef4444") : undefined }}
                >
                  {h.change_pct != null ? `${h.change_pct >= 0 ? "+" : ""}${h.change_pct.toFixed(2)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
