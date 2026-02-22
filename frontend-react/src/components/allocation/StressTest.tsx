import { useState, useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Skeleton } from "@/components/ui/skeleton"
import { useStressTest } from "@/api/hooks/useAllocation"

interface Props {
  displayCurrency: string
  privacyMode: boolean
  enabled: boolean
}

const PAIN_COLORS: Record<string, string> = {
  low: "#22c55e",
  moderate: "#f59e0b",
  high: "#f97316",
  panic: "#ef4444",
}

function fmtValue(v: number, currency: string, privacyMode: boolean): string {
  if (privacyMode) return "***"
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(v)
}

export function StressTest({ displayCurrency, privacyMode, enabled }: Props) {
  const { t } = useTranslation()
  const [sliderValue, setSliderValue] = useState(20)
  const [debouncedDrop, setDebouncedDrop] = useState(20)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setDebouncedDrop(sliderValue), 300)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [sliderValue])

  const { data, isLoading } = useStressTest(-debouncedDrop, displayCurrency, enabled)

  const painColor = data ? (PAIN_COLORS[data.pain_level.level] ?? "#9ca3af") : "#9ca3af"

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold">{t("allocation.stress.title")}</p>

      {/* Slider */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t("allocation.stress.slider_label")}</span>
          <span className="text-sm font-semibold text-red-500">-{sliderValue}%</span>
        </div>
        <input
          type="range"
          min={5}
          max={50}
          step={5}
          value={sliderValue}
          onChange={(e) => setSliderValue(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>-5%</span>
          <span>-50%</span>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : !data ? null : (
        <>
          {/* Metrics row */}
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="rounded-lg border border-border p-3">
              <p className="text-muted-foreground">{t("allocation.stress.beta")}</p>
              <p className="text-xl font-bold">{data.portfolio_beta.toFixed(2)}</p>
            </div>
            <div className="rounded-lg border border-border p-3">
              <p className="text-muted-foreground">{t("allocation.stress.loss")}</p>
              <p className="text-xl font-bold text-red-500">
                {privacyMode ? "***" : `-${data.total_loss_pct.toFixed(1)}%`}
              </p>
              <p className="text-xs text-muted-foreground">
                {fmtValue(data.total_loss, data.display_currency, privacyMode)}
              </p>
            </div>
            <div className="rounded-lg border border-border p-3" style={{ borderColor: `${painColor}40`, backgroundColor: `${painColor}10` }}>
              <p className="text-muted-foreground">{t("allocation.stress.pain_level")}</p>
              <p className="text-base font-bold" style={{ color: painColor }}>
                {data.pain_level.emoji} {data.pain_level.label}
              </p>
            </div>
          </div>

          {/* Advice */}
          {data.advice.length > 0 && (
            <ul className="space-y-1">
              {data.advice.map((a, i) => (
                <li key={i} className="text-xs text-muted-foreground">• {a}</li>
              ))}
            </ul>
          )}

          {/* Holdings breakdown */}
          <section className="space-y-1">
            <p className="text-sm font-semibold">{t("allocation.stress.breakdown_title")}</p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
                    <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
                    <th className="text-right py-0.5 pr-2">{t("allocation.stress.col_beta")}</th>
                    <th className="text-right py-0.5 pr-2">{t("allocation.stress.col_drop")}</th>
                    <th className="text-right py-0.5">{t("allocation.stress.col_loss")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.holdings_breakdown.map((h, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                      <td className="py-0.5 pr-2 text-muted-foreground">{h.category}</td>
                      <td className="py-0.5 pr-2 text-right">{h.beta.toFixed(2)}</td>
                      <td className="py-0.5 pr-2 text-right text-red-500">
                        -{h.expected_drop_pct.toFixed(1)}%
                      </td>
                      <td className="py-0.5 text-right text-red-500">
                        {privacyMode ? "***" : fmtValue(h.expected_loss, data.display_currency, false)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Disclaimer */}
          {data.disclaimer && (
            <p className="text-xs text-muted-foreground italic">{data.disclaimer}</p>
          )}
        </>
      )}
    </div>
  )
}
