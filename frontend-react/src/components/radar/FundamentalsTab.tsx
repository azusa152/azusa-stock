import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { FundamentalsSheet } from "@/components/radar/FundamentalsSheet"
import type { RadarFundamentals } from "@/api/types/radar"
import { formatMarketCap, formatPercent, formatRatio } from "@/lib/format"
import { getHealthColor } from "@/lib/constants"
import { FINANCE_CHIP } from "@/lib/colors"

interface Props {
  ticker: string
  fundamentals?: RadarFundamentals
}

function HealthPill({ metric, value }: { metric: string; value?: number | null }) {
  if (value == null) return null
  const color = getHealthColor(metric, value)
  const klass =
    color === "green"
      ? FINANCE_CHIP.gain
      : color === "red"
        ? FINANCE_CHIP.loss
        : FINANCE_CHIP.warning
  return (
    <span className={`rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${klass}`}>
      {color}
    </span>
  )
}

function MetricItem({
  label,
  value,
  explanation,
  metricKey,
  metricValue,
}: {
  label: string
  value: string
  explanation: string
  metricKey?: string
  metricValue?: number | null
}) {
  const numeric = metricValue

  return (
    <div className="rounded border border-border/60 p-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium">{label}</p>
        {metricKey && numeric != null && <HealthPill metric={metricKey} value={numeric} />}
      </div>
      <p className="text-sm font-semibold">{value}</p>
      <p className="text-xs text-muted-foreground">{explanation}</p>
    </div>
  )
}

export function FundamentalsTab({ ticker, fundamentals }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  if (!fundamentals) {
    return <p className="text-xs text-muted-foreground">{t("radar.stock_card.fundamentals.no_data")}</p>
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <p className="text-xs font-semibold text-muted-foreground">{t("radar.stock_card.fundamentals.affordable")}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <MetricItem
            label={t("radar.stock_card.fundamentals.trailing_pe")}
            value={formatRatio(fundamentals.trailing_pe)}
            explanation={t("radar.stock_card.fundamentals.trailing_pe_tip")}
            metricKey="trailing_pe"
            metricValue={fundamentals.trailing_pe}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.price_to_book")}
            value={formatRatio(fundamentals.price_to_book)}
            explanation={t("radar.stock_card.fundamentals.price_to_book_tip")}
            metricKey="price_to_book"
            metricValue={fundamentals.price_to_book}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.price_to_sales")}
            value={formatRatio(fundamentals.price_to_sales)}
            explanation={t("radar.stock_card.fundamentals.price_to_sales_tip")}
          />
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-semibold text-muted-foreground">{t("radar.stock_card.fundamentals.profitable")}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <MetricItem
            label={t("radar.stock_card.fundamentals.return_on_equity")}
            value={formatPercent(fundamentals.return_on_equity)}
            explanation={t("radar.stock_card.fundamentals.return_on_equity_tip")}
            metricKey="return_on_equity"
            metricValue={fundamentals.return_on_equity}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.profit_margins")}
            value={formatPercent(fundamentals.profit_margins)}
            explanation={t("radar.stock_card.fundamentals.profit_margins_tip")}
            metricKey="profit_margins"
            metricValue={fundamentals.profit_margins}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.operating_margins")}
            value={formatPercent(fundamentals.operating_margins)}
            explanation={t("radar.stock_card.fundamentals.operating_margins_tip")}
            metricKey="operating_margins"
            metricValue={fundamentals.operating_margins}
          />
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-semibold text-muted-foreground">{t("radar.stock_card.fundamentals.growing")}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <MetricItem
            label={t("radar.stock_card.fundamentals.revenue_growth")}
            value={formatPercent(fundamentals.revenue_growth)}
            explanation={t("radar.stock_card.fundamentals.revenue_growth_tip")}
            metricKey="revenue_growth"
            metricValue={fundamentals.revenue_growth}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.earnings_growth")}
            value={formatPercent(fundamentals.earnings_growth)}
            explanation={t("radar.stock_card.fundamentals.earnings_growth_tip")}
            metricKey="earnings_growth"
            metricValue={fundamentals.earnings_growth}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.trailing_eps")}
            value={formatRatio(fundamentals.trailing_eps)}
            explanation={t("radar.stock_card.fundamentals.trailing_eps_tip")}
          />
          <MetricItem
            label={t("radar.stock_card.fundamentals.forward_eps")}
            value={formatRatio(fundamentals.forward_eps)}
            explanation={t("radar.stock_card.fundamentals.forward_eps_tip")}
          />
        </div>
      </div>

      <div className="space-y-1">
        <p className="text-xs font-semibold text-muted-foreground">{t("radar.stock_card.fundamentals.size")}</p>
        <div className="grid grid-cols-1 gap-2">
          <MetricItem
            label={t("radar.stock_card.fundamentals.market_cap")}
            value={formatMarketCap(fundamentals.market_cap)}
            explanation={t("radar.stock_card.fundamentals.market_cap_tip")}
          />
        </div>
      </div>

      <div className="pt-1">
        <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
          {t("radar.stock_card.fundamentals.more_details")}
        </Button>
      </div>
      <FundamentalsSheet
        ticker={ticker}
        open={open}
        onOpenChange={setOpen}
        initialData={fundamentals}
      />
    </div>
  )
}
