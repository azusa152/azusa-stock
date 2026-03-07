import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { GreatMindsResponse } from "@/api/types/dashboard"

const HOLDING_ACTION_ICONS: Record<string, string> = {
  NEW: "🆕",
  ADD: "📈",
  REDUCE: "📉",
  SOLD_OUT: "❌",
  UNCHANGED: "⚪",
}

function getActionLabel(action: string): string {
  const labels: Record<string, string> = {
    NEW: "New",
    ADD: "Add",
    REDUCE: "Reduce",
    SOLD_OUT: "Sold Out",
    UNCHANGED: "Unchanged",
  }
  return labels[action] ?? action
}

interface Props {
  greatMinds?: GreatMindsResponse | null
  isLoading?: boolean
}

export function ResonanceSummary({ greatMinds, isLoading }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t("dashboard.resonance.title")}</CardTitle>
          <Button size="sm" variant="outline" onClick={() => navigate("/smart-money")}>
            {t("dashboard.resonance.goto_smart_money")}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
        ) : greatMinds == null ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.resonance.unavailable")}</p>
        ) : greatMinds.total_count === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.resonance.empty")}</p>
        ) : (
          <div className="space-y-4">
            {/* Always-visible KPI row */}
            <div className="grid grid-cols-1 gap-4 text-center sm:grid-cols-3">
              <div>
                <p className="text-2xl font-bold">{greatMinds.total_count}</p>
                <p className="text-xs text-muted-foreground">{t("dashboard.resonance.overlap_count")}</p>
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {new Set(greatMinds.stocks.flatMap((s) => s.gurus.map((g) => g.guru_id))).size}
                </p>
                <p className="text-xs text-muted-foreground">{t("dashboard.resonance.gurus_with_overlap")}</p>
              </div>
              <div>
                <p className="text-lg font-bold">
                  {greatMinds.stocks[0]
                    ? `${greatMinds.stocks[0].ticker} ×${greatMinds.stocks[0].guru_count}`
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground">{t("dashboard.resonance.strongest_signal")}</p>
              </div>
            </div>

            {/* Expandable detail */}
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
            >
              <span className="inline-flex items-center gap-1">
                <ChevronDown className={cn("h-3.5 w-3.5 transition-transform duration-200", expanded && "rotate-180")} />
                {t("dashboard.resonance.details_expander")}
              </span>
            </button>

            {expanded && (
              <div className="space-y-2">
                {greatMinds.stocks.slice(0, 5).map((stock) => (
                  <div key={stock.ticker} className="rounded-md border border-border p-3 text-sm">
                    <p className="font-semibold">
                      {stock.ticker} ×{stock.guru_count}
                    </p>
                    <div className="mt-1 space-y-0.5">
                      {stock.gurus.map((g, i) => {
                        const icon = HOLDING_ACTION_ICONS[g.action] ?? "⚪"
                        const label = getActionLabel(g.action)
                        const weight = g.weight_pct != null && g.action !== "SOLD_OUT"
                          ? ` ${g.weight_pct.toFixed(1)}%`
                          : ""
                        return (
                          <p key={i} className="text-xs text-muted-foreground">
                            {g.guru_display_name} {icon} {label}{weight}
                          </p>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <p className="text-xs text-muted-foreground">{t("dashboard.resonance.caption")}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
