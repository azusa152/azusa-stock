import { useState } from "react"
import { useTranslation } from "react-i18next"
import { formatValue } from "./formatters"
import type { SeasonHighlights as SeasonHighlightsType } from "@/api/types/smartMoney"

const TOP_N = 5

interface Props {
  data: SeasonHighlightsType
}

export function SeasonHighlights({ data }: Props) {
  const { t } = useTranslation()
  const [showAllNew, setShowAllNew] = useState(false)
  const [showAllSold, setShowAllSold] = useState(false)

  const { new_positions, sold_outs } = data

  if (new_positions.length === 0 && sold_outs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">{t("smart_money.overview.highlights_empty")}</p>
    )
  }

  const totalNewValue = new_positions.reduce((sum, h) => sum + h.value, 0)

  const visibleNew = showAllNew ? new_positions : new_positions.slice(0, TOP_N)
  const visibleSold = showAllSold ? sold_outs : sold_outs.slice(0, TOP_N)

  return (
    <div className="space-y-3">
      {/* Summary metrics */}
      <div className="flex flex-wrap gap-4 text-xs">
        <div>
          <span className="font-semibold text-green-500">{new_positions.length}</span>{" "}
          {t("smart_money.overview.highlights_new_count")}
        </div>
        <div>
          <span className="font-semibold text-red-500">{sold_outs.length}</span>{" "}
          {t("smart_money.overview.highlights_sold_count")}
        </div>
        <div>
          <span className="font-semibold">{formatValue(totalNewValue)}</span>{" "}
          {t("smart_money.overview.highlights_total_value")}
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* New positions */}
        {new_positions.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-semibold text-green-600">
              {t("smart_money.overview.new_positions_header")}
            </p>
            {visibleNew.map((item, i) => (
              <div
                key={`${item.ticker ?? "null"}-${item.guru_id}-${i}`}
                className="flex items-center justify-between gap-2 text-xs border-b border-border pb-1"
              >
                <div className="min-w-0">
                  <span className="font-medium">{item.ticker ?? "—"}</span>
                  <span className="text-muted-foreground ml-1 truncate">
                    {item.company_name}
                  </span>
                  <span className="block text-muted-foreground">{item.guru_display_name}</span>
                </div>
                <div className="text-right shrink-0">
                  <span className="block">{formatValue(item.value)}</span>
                  {item.weight_pct != null && (
                    <span className="text-muted-foreground">{item.weight_pct.toFixed(1)}%</span>
                  )}
                </div>
              </div>
            ))}
            {new_positions.length > TOP_N && !showAllNew && (
              <button
                onClick={() => setShowAllNew(true)}
                className="text-xs text-primary underline"
              >
                {t("smart_money.overview.highlights_show_all", {
                  count: new_positions.length - TOP_N,
                })}
              </button>
            )}
          </div>
        )}

        {/* Sold outs */}
        {sold_outs.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-semibold text-red-600">
              {t("smart_money.overview.sold_outs_header")}
            </p>
            {visibleSold.map((item, i) => (
              <div
                key={`${item.ticker ?? "null"}-${item.guru_id}-${i}`}
                className="flex items-center justify-between gap-2 text-xs border-b border-border pb-1"
              >
                <div className="min-w-0">
                  <span className="font-medium">{item.ticker ?? "—"}</span>
                  <span className="text-muted-foreground ml-1 truncate">
                    {item.company_name}
                  </span>
                  <span className="block text-muted-foreground">{item.guru_display_name}</span>
                </div>
                <div className="text-right shrink-0">
                  <span className="block">{formatValue(item.value)}</span>
                  {item.weight_pct != null && (
                    <span className="text-muted-foreground">{item.weight_pct.toFixed(1)}%</span>
                  )}
                </div>
              </div>
            ))}
            {sold_outs.length > TOP_N && !showAllSold && (
              <button
                onClick={() => setShowAllSold(true)}
                className="text-xs text-primary underline"
              >
                {t("smart_money.overview.highlights_show_all", {
                  count: sold_outs.length - TOP_N,
                })}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
