import { useTranslation } from "react-i18next"
import type { ConsensusStockItem } from "@/api/types/smartMoney"

interface Props {
  items: ConsensusStockItem[]
}

export function ConsensusStocks({ items }: Props) {
  const { t } = useTranslation()

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t("smart_money.overview.consensus_empty")}</p>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.ticker}
          className="flex items-center gap-3 rounded-md border border-border p-2"
        >
          <span className="text-lg font-bold w-20 shrink-0">{item.ticker}</span>
          <div className="min-w-0 flex-1">
            <p className="text-xs text-muted-foreground">{item.gurus.join(", ")}</p>
          </div>
          <div className="text-right shrink-0">
            <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              {item.guru_count} {t("smart_money.overview.consensus_gurus")}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
