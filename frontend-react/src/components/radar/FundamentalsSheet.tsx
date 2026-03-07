import { useTranslation } from "react-i18next"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useFundamentals } from "@/api/hooks/useRadar"
import type { RadarFundamentals } from "@/api/types/radar"
import { formatMarketCap, formatPercent, formatRatio } from "@/lib/format"
import { getHealthColor } from "@/lib/constants"
import { FINANCE_CHIP } from "@/lib/colors"

interface Props {
  ticker: string
  open: boolean
  onOpenChange: (open: boolean) => void
  initialData?: RadarFundamentals
}

function hasMeaningfulMetrics(data?: RadarFundamentals): boolean {
  if (!data) return false
  return Object.entries(data).some(
    ([key, value]) => key !== "ticker" && typeof value === "number" && !Number.isNaN(value),
  )
}

function HealthBadge({ metric, value }: { metric: string; value?: number | null }) {
  if (value == null) return null
  const color = getHealthColor(metric, value)
  const klass =
    color === "green"
      ? FINANCE_CHIP.gain
      : color === "red"
        ? FINANCE_CHIP.loss
        : FINANCE_CHIP.warning
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${klass}`}>
      {color}
    </span>
  )
}

function MetricRow({
  label,
  value,
  tip,
  metricKey,
  metricValue,
}: {
  label: string
  value: string
  tip: string
  metricKey?: string
  metricValue?: number | null
}) {
  return (
    <div className="rounded-md border border-border/70 p-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium">{label}</p>
        {metricKey && metricValue != null && (
          <HealthBadge metric={metricKey} value={metricValue} />
        )}
      </div>
      <p className="text-sm font-semibold mt-0.5">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{tip}</p>
    </div>
  )
}

function renderRows(t: (key: string) => string, f?: RadarFundamentals) {
  return [
    {
      label: t("radar.stock_card.fundamentals.market_cap"),
      value: formatMarketCap(f?.market_cap),
      tip: t("radar.stock_card.fundamentals.market_cap_tip"),
    },
    {
      label: t("radar.stock_card.fundamentals.trailing_pe"),
      value: formatRatio(f?.trailing_pe),
      tip: t("radar.stock_card.fundamentals.trailing_pe_tip"),
      metricKey: "trailing_pe",
      metricValue: f?.trailing_pe,
    },
    {
      label: t("radar.stock_card.fundamentals.forward_pe"),
      value: formatRatio(f?.forward_pe),
      tip: t("radar.stock_card.fundamentals.forward_pe_tip"),
      metricKey: "forward_pe",
      metricValue: f?.forward_pe,
    },
    {
      label: t("radar.stock_card.fundamentals.trailing_eps"),
      value: formatRatio(f?.trailing_eps),
      tip: t("radar.stock_card.fundamentals.trailing_eps_tip"),
    },
    {
      label: t("radar.stock_card.fundamentals.forward_eps"),
      value: formatRatio(f?.forward_eps),
      tip: t("radar.stock_card.fundamentals.forward_eps_tip"),
    },
    {
      label: t("radar.stock_card.fundamentals.price_to_book"),
      value: formatRatio(f?.price_to_book),
      tip: t("radar.stock_card.fundamentals.price_to_book_tip"),
      metricKey: "price_to_book",
      metricValue: f?.price_to_book,
    },
    {
      label: t("radar.stock_card.fundamentals.price_to_sales"),
      value: formatRatio(f?.price_to_sales),
      tip: t("radar.stock_card.fundamentals.price_to_sales_tip"),
    },
    {
      label: t("radar.stock_card.fundamentals.return_on_equity"),
      value: formatPercent(f?.return_on_equity),
      tip: t("radar.stock_card.fundamentals.return_on_equity_tip"),
      metricKey: "return_on_equity",
      metricValue: f?.return_on_equity,
    },
    {
      label: t("radar.stock_card.fundamentals.profit_margins"),
      value: formatPercent(f?.profit_margins),
      tip: t("radar.stock_card.fundamentals.profit_margins_tip"),
      metricKey: "profit_margins",
      metricValue: f?.profit_margins,
    },
    {
      label: t("radar.stock_card.fundamentals.operating_margins"),
      value: formatPercent(f?.operating_margins),
      tip: t("radar.stock_card.fundamentals.operating_margins_tip"),
      metricKey: "operating_margins",
      metricValue: f?.operating_margins,
    },
    {
      label: t("radar.stock_card.fundamentals.revenue_growth"),
      value: formatPercent(f?.revenue_growth),
      tip: t("radar.stock_card.fundamentals.revenue_growth_tip"),
      metricKey: "revenue_growth",
      metricValue: f?.revenue_growth,
    },
    {
      label: t("radar.stock_card.fundamentals.earnings_growth"),
      value: formatPercent(f?.earnings_growth),
      tip: t("radar.stock_card.fundamentals.earnings_growth_tip"),
      metricKey: "earnings_growth",
      metricValue: f?.earnings_growth,
    },
  ]
}

export function FundamentalsSheet({ ticker, open, onOpenChange, initialData }: Props) {
  const { t } = useTranslation()
  const shouldFetch = open && !hasMeaningfulMetrics(initialData)
  const { data, isLoading } = useFundamentals(ticker, shouldFetch)
  const fundamentals = initialData ?? data
  const rows = renderRows(t, fundamentals)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[95vw] sm:w-[34rem] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            {ticker} · {t("radar.stock_card.fundamentals.sheet_title")}
          </SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-2">
          {shouldFetch && isLoading ? (
            <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : (
            rows.map((row) => (
              <MetricRow
                key={row.label}
                label={row.label}
                value={row.value}
                tip={row.tip}
                metricKey={row.metricKey}
                metricValue={row.metricValue}
              />
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
