import { useState } from "react"
import { useTranslation } from "react-i18next"
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, LabelList, ResponsiveContainer } from "recharts"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import {
  useGuruFiling,
  useGuruFilings,
  useGuruHoldingChanges,
  useGuruTopHoldings,
  useGreatMinds,
  useSyncGuru,
} from "@/api/hooks/useSmartMoney"
import { formatValue, formatShares, ACTION_COLORS, ACTION_ICONS, isStale } from "./formatters"
import { ActionBadge } from "./ActionBadge"
import type { GuruHolding } from "@/api/types/smartMoney"

interface Props {
  guruId: number
  guruName: string
  enabled: boolean
}

function groupByAction(holdings: GuruHolding[]): Map<string, GuruHolding[]> {
  const map = new Map<string, GuruHolding[]>()
  for (const h of holdings) {
    const arr = map.get(h.action) ?? []
    arr.push(h)
    map.set(h.action, arr)
  }
  return map
}

const ACTION_ORDER = ["NEW_POSITION", "SOLD_OUT", "INCREASED", "DECREASED", "UNCHANGED"]

export function GuruTab({ guruId, guruName, enabled }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const [historyOpen, setHistoryOpen] = useState(false)
  const [greatMindsOpen, setGreatMindsOpen] = useState(false)

  const syncMutation = useSyncGuru()
  const syncing = syncMutation.isPending && syncMutation.variables === guruId

  const { data: filing, isLoading: filingLoading } = useGuruFiling(guruId, enabled)
  const { data: filingsResp } = useGuruFilings(guruId, enabled && historyOpen)
  const { data: changes, isLoading: changesLoading } = useGuruHoldingChanges(guruId, enabled)
  const { data: topHoldings, isLoading: topLoading } = useGuruTopHoldings(guruId, enabled)
  const { data: greatMinds } = useGreatMinds()

  if (!enabled) return null

  // -------------------------------------------------------------------------
  // Filing meta section
  // -------------------------------------------------------------------------
  const filingSection = (
    <section className="space-y-2">
      {/* Sync button row */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          onClick={() => syncMutation.mutate(guruId)}
          disabled={syncMutation.isPending}
        >
          {syncing ? t("smart_money.sidebar.syncing") : t("smart_money.sidebar.sync_button")}
        </Button>
        {syncMutation.isSuccess && syncMutation.variables === guruId && (
          <span className="text-xs text-muted-foreground">{t("smart_money.sidebar.sync_success")}</span>
        )}
        {syncMutation.isError && syncMutation.variables === guruId && (
          <span className="text-xs text-destructive">{t("smart_money.sidebar.sync_error", { msg: "" })}</span>
        )}
      </div>

      {filingLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-3/4" />
        </div>
      ) : !filing ? (
        <p className="text-sm text-muted-foreground">{t("smart_money.no_filing", { guru: guruName })}</p>
      ) : (
        <>
          {/* Stale warning */}
          {isStale(filing.report_date) && (
            <div className="rounded-md border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-700 dark:text-yellow-400">
              {t("smart_money.lagging_banner", {
                report_date: filing.report_date ?? "—",
                filing_date: filing.filing_date ?? "—",
              })}
            </div>
          )}

          {/* Metrics row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <div>
              <p className="text-muted-foreground">{t("smart_money.metric.report_date")}</p>
              <p className="font-semibold">{filing.report_date ?? "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t("smart_money.metric.filing_date")}</p>
              <p className="font-semibold">{filing.filing_date ?? "—"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t("smart_money.metric.total_value")}</p>
              <p className="font-semibold">{formatValue(filing.total_value)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">{t("smart_money.metric.holdings_count")}</p>
              <p className="font-semibold">{filing.holdings_count}</p>
            </div>
          </div>

          {/* EDGAR link */}
          {filing.filing_url && (
            <a
              href={filing.filing_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-xs text-primary underline"
            >
              {t("smart_money.edgar_link")}
            </a>
          )}

          {/* Filing history collapsible */}
          <button
            onClick={() => setHistoryOpen((v) => !v)}
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            {filingsResp
              ? t("smart_money.overview.filing_history_expander", {
                  count: filingsResp.filings.length,
                })
              : t("smart_money.tab.changes")}
            <span>{historyOpen ? "▲" : "▼"}</span>
          </button>
          {historyOpen && filingsResp && (
            <div className="space-y-0.5 pl-2 border-l border-border">
              {filingsResp.filings.map((f) => (
                <p key={f.id} className="text-xs text-muted-foreground">
                  {t("smart_money.overview.filing_history_row", {
                    report_date: f.report_date,
                    filing_date: f.filing_date,
                    total_value: formatValue(f.total_value),
                    holdings_count: f.holdings_count,
                  })}
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )

  // -------------------------------------------------------------------------
  // Holding changes section
  // -------------------------------------------------------------------------
  const holdingChangesSection = (
    <section className="space-y-2">
      <p className="text-sm font-semibold">{t("smart_money.tab.changes")}</p>
      {changesLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : !changes || changes.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("smart_money.changes.no_changes")}</p>
      ) : (
        <>
          {/* Action summary badges */}
          <div className="flex flex-wrap gap-2 text-xs">
            {(["NEW_POSITION", "SOLD_OUT", "INCREASED", "DECREASED"] as const).map((action) => {
              const count = changes.filter((c) => c.action === action).length
              if (count === 0) return null
              return (
                <span
                  key={action}
                  style={{ color: ACTION_COLORS[action] }}
                  className="font-semibold"
                >
                  {ACTION_ICONS[action]} {count}
                </span>
              )
            })}
          </div>

          {/* Changes table grouped by action */}
          {(() => {
            const grouped = groupByAction(changes)
            return ACTION_ORDER.map((action) => {
            const items = grouped.get(action)
            if (!items || items.length === 0) return null
            return (
              <div key={action} className="space-y-1">
                <p
                  className="text-xs font-semibold"
                  style={{ color: ACTION_COLORS[action] ?? "#9ca3af" }}
                >
                  {ACTION_ICONS[action]} {t(`smart_money.action.${action.toLowerCase()}`, { defaultValue: action })}
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-muted-foreground border-b border-border">
                        <th className="text-left py-0.5 pr-2">{t("smart_money.col.ticker")}</th>
                        <th className="text-left py-0.5 pr-2">{t("smart_money.col.company")}</th>
                        <th className="text-right py-0.5 pr-2">{t("smart_money.col.value")}</th>
                        <th className="text-right py-0.5 pr-2">{t("smart_money.col.shares")}</th>
                        <th className="text-right py-0.5 pr-2">{t("smart_money.col.change_pct")}</th>
                        <th className="text-right py-0.5">{t("smart_money.col.weight_pct")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((h, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-0.5 pr-2 font-medium">{h.ticker ?? "—"}</td>
                          <td className="py-0.5 pr-2 text-muted-foreground max-w-[120px] truncate">
                            {h.company_name}
                          </td>
                          <td className="py-0.5 pr-2 text-right">{formatValue(h.value)}</td>
                          <td className="py-0.5 pr-2 text-right">{formatShares(h.shares)}</td>
                          <td className="py-0.5 pr-2 text-right">
                            {h.change_pct != null ? `${h.change_pct.toFixed(1)}%` : "—"}
                          </td>
                          <td className="py-0.5 text-right">
                            {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })
          })()}
        </>
      )}
    </section>
  )

  // -------------------------------------------------------------------------
  // Top holdings section
  // -------------------------------------------------------------------------
  const topHoldingsSection = (
    <section className="space-y-2">
      <p className="text-sm font-semibold">{t("smart_money.tab.top")}</p>
      {topLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : !topHoldings || topHoldings.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("smart_money.top.no_data")}</p>
      ) : (
        <>
          {/* Horizontal bar chart */}
          {(() => {
            const barData = topHoldings.map((h) => ({
              name: h.ticker ?? h.company_name,
              weight: h.weight_pct ?? 0,
              fill: ACTION_COLORS[h.action] ?? ACTION_COLORS.UNCHANGED,
            }))
            const chartH = Math.max(180, topHoldings.length * 22 + 50)
            return (
              <ResponsiveContainer width="100%" height={chartH}>
                <BarChart data={barData} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 20 }}>
                  <XAxis
                    type="number"
                    tick={{ fontSize: 9, fill: theme.tickColor }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `${v}%`}
                    label={{ value: t("smart_money.top.weight_axis"), position: "insideBottom", offset: -10, fontSize: 10, fill: theme.tickColor }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 9, fill: theme.tickColor }}
                    axisLine={false}
                    tickLine={false}
                    width={60}
                  />
                  <Tooltip
                    contentStyle={theme.tooltipStyle}
                    formatter={(v: number | undefined) => [`${v != null ? v.toFixed(2) : ""}%`, t("smart_money.top.weight_axis")]}
                    labelStyle={{ color: theme.tooltipText }}
                    cursor={{ fill: "rgba(128,128,128,0.08)" }}
                  />
                  <Bar dataKey="weight" radius={[0, 3, 3, 0]}>
                    {barData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                    <LabelList
                      dataKey="weight"
                      position="right"
                      formatter={(v: unknown) => typeof v === "number" ? `${v.toFixed(1)}%` : ""}
                      style={{ fontSize: 9, fill: theme.tickColor }}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )
          })()}

          {/* Detail table */}
          <p className="text-xs font-semibold">{t("smart_money.top.table_title")}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground border-b border-border">
                  <th className="text-left py-0.5 pr-2">{t("smart_money.col.rank")}</th>
                  <th className="text-left py-0.5 pr-2">{t("smart_money.col.ticker")}</th>
                  <th className="text-left py-0.5 pr-2">{t("smart_money.col.company")}</th>
                  <th className="text-left py-0.5 pr-2">{t("smart_money.col.action")}</th>
                  <th className="text-right py-0.5 pr-2">{t("smart_money.col.weight_pct")}</th>
                  <th className="text-right py-0.5 pr-2">{t("smart_money.col.value")}</th>
                  <th className="text-right py-0.5">{t("smart_money.col.shares")}</th>
                </tr>
              </thead>
              <tbody>
                {topHoldings.map((h, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-0.5 pr-2 text-muted-foreground">{i + 1}</td>
                    <td className="py-0.5 pr-2 font-medium">{h.ticker ?? "—"}</td>
                    <td className="py-0.5 pr-2 text-muted-foreground max-w-[120px] truncate">
                      {h.company_name}
                    </td>
                    <td className="py-0.5 pr-2">
                      <ActionBadge action={h.action} />
                    </td>
                    <td className="py-0.5 pr-2 text-right">
                      {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-0.5 pr-2 text-right">{formatValue(h.value)}</td>
                    <td className="py-0.5 text-right">{formatShares(h.shares)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )

  // -------------------------------------------------------------------------
  // Great Minds section
  // -------------------------------------------------------------------------
  const guruStocks = greatMinds?.stocks.filter((s) =>
    s.gurus.some((g) => g.guru_id === guruId),
  )

  const greatMindsSection = (
    <section className="space-y-2">
      <button
        onClick={() => setGreatMindsOpen((v) => !v)}
        className="flex items-center gap-1 text-sm font-semibold"
      >
        {t("smart_money.tab.great_minds")}
        <span className="text-muted-foreground text-xs">{greatMindsOpen ? "▲" : "▼"}</span>
      </button>
      {greatMindsOpen && (
        <>
          {!guruStocks || guruStocks.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("smart_money.great_minds.empty")}</p>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                {t("smart_money.great_minds.overlap_count")}: {guruStocks.length}
              </p>
              {guruStocks.map((stock) => (
                <div
                  key={stock.ticker}
                  className="flex items-start gap-3 rounded-md border border-border p-2"
                >
                  <span className="text-base font-bold w-16 shrink-0">{stock.ticker}</span>
                  <div className="min-w-0 flex-1 text-xs space-y-0.5">
                    {stock.gurus.map((g, gi) => (
                      <p key={gi} className="text-muted-foreground">
                        {g.guru_display_name} — <ActionBadge action={g.action} />{" "}
                        {g.weight_pct != null ? `${g.weight_pct.toFixed(1)}%` : ""}
                      </p>
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {stock.guru_count} {t("smart_money.great_minds.guru_count_label")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )

  return (
    <div className="space-y-6">
      {filingSection}
      <hr className="border-border" />
      {holdingChangesSection}
      <hr className="border-border" />
      {topHoldingsSection}
      <hr className="border-border" />
      {greatMindsSection}
    </div>
  )
}
