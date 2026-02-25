import { useTranslation } from "react-i18next"
import { ActionBadge } from "./ActionBadge"
import { formatValue } from "./formatters"
import type { ConsensusStockItem } from "@/api/types/smartMoney"

export function ConsensusStocks({ items }: { items: ConsensusStockItem[] }) {
  const { t } = useTranslation()

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("smart_money.overview.consensus_empty")}
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.ticker} className="rounded-md border border-border p-3 space-y-1.5">
          {/* Header row */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-sm">{item.ticker}</span>
              <span className="text-xs text-muted-foreground truncate max-w-[180px]">
                {item.company_name}
              </span>
              {item.sector && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                  {item.sector}
                </span>
              )}
            </div>
            <div className="shrink-0 text-right text-xs">
              <span className="font-semibold">
                {item.guru_count} {t("smart_money.overview.consensus_gurus")}
              </span>
              {item.avg_weight_pct != null && (
                <span className="text-muted-foreground ml-1">
                  {t("smart_money.overview.avg_weight_label")} {item.avg_weight_pct.toFixed(1)}%
                </span>
              )}
              <span className="text-muted-foreground ml-1">{formatValue(item.total_value)}</span>
            </div>
          </div>

          {/* Per-guru action row */}
          <div className="flex flex-wrap gap-x-3 gap-y-0.5">
            {item.gurus.map((g, i) => (
              <span key={i} className="text-xs text-muted-foreground">
                {g.display_name}
                <span className="ml-1">
                  <ActionBadge action={g.action} />
                </span>
                {g.weight_pct != null && (
                  <span className="ml-1">{g.weight_pct.toFixed(1)}%</span>
                )}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
