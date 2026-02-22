import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { SCAN_SIGNAL_ICONS, CATEGORY_ICON_SHORT, STOCK_CATEGORIES } from "@/lib/constants"
import { useAddThesis, useUpdateCategory, useDeactivateStock, useThesisHistory } from "@/api/hooks/useRadar"
import type { RadarStock, RadarEnrichedStock, ResonanceMap, StockCategory } from "@/api/types/radar"

const SKIP_DIVIDEND_CATEGORIES = new Set(["Trend_Setter", "Growth", "Cash"])

function infer_market_label(ticker: string): string {
  if (ticker.endsWith(".TW")) return "🇹🇼 TW"
  if (ticker.endsWith(".T")) return "🇯🇵 JP"
  if (ticker.endsWith(".HK")) return "🇭🇰 HK"
  return "🇺🇸 US"
}

interface Props {
  stock: RadarStock
  enrichment?: RadarEnrichedStock
  resonance?: ResonanceMap[string]
}

function MetricChip({ label, value, color }: { label: string; value: string | number | null | undefined; color?: string }) {
  if (value == null) return null
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${color ?? "border-border text-foreground"}`}>
      {label}: {value}
    </span>
  )
}

function ThesisSection({ ticker, stock }: { ticker: string; stock: RadarStock }) {
  const { t } = useTranslation()
  const [thesisText, setThesisText] = useState("")
  const [tags, setTagsText] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)
  const addThesis = useAddThesis()

  const handleSubmit = () => {
    if (!thesisText.trim()) {
      setFeedback(t("radar.stock_card.error_no_thesis"))
      return
    }
    const tagList = tags
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    addThesis.mutate(
      { ticker, payload: { content: thesisText.trim(), tags: tagList.length ? tagList : stock.current_tags } },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          setThesisText("")
          setTagsText("")
        },
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-2">
      <textarea
        className="w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
        rows={3}
        placeholder={t("radar.stock_card.update_thesis_placeholder")}
        value={thesisText}
        onChange={(e) => setThesisText(e.target.value)}
      />
      <input
        className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
        placeholder={t("radar.stock_card.tags_placeholder")}
        value={tags}
        onChange={(e) => setTagsText(e.target.value)}
      />
      <Button size="sm" onClick={handleSubmit} disabled={addThesis.isPending}>
        {t("radar.stock_card.update_button")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

function ThesisHistorySection({ ticker }: { ticker: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: history, isLoading } = useThesisHistory(ticker, open)

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
      >
        {open ? "▲" : "▼"} {t("radar.stock_card.history")}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {isLoading ? (
            <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
          ) : !history?.length ? (
            <p className="text-xs text-muted-foreground">{t("radar.stock_card.no_history")}</p>
          ) : (
            history.map((entry) => (
              <div key={entry.version} className="rounded border border-border p-2 text-xs">
                <p className="font-semibold text-muted-foreground">
                  v{entry.version} — {entry.created_at.slice(0, 10)}
                </p>
                <p className="mt-0.5">{entry.content}</p>
                {entry.tags.length > 0 && (
                  <p className="mt-0.5 text-muted-foreground">{entry.tags.map((tag) => `#${tag}`).join(" ")}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function ChangeCategorySection({ ticker, currentCategory }: { ticker: string; currentCategory: StockCategory }) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<StockCategory>(
    STOCK_CATEGORIES.find((c) => c !== currentCategory) ?? "Growth",
  )
  const [feedback, setFeedback] = useState<string | null>(null)
  const updateCategory = useUpdateCategory()

  const others = STOCK_CATEGORIES.filter((c) => c !== currentCategory)

  const handleConfirm = () => {
    updateCategory.mutate(
      { ticker, payload: { category: selected } },
      {
        onSuccess: (data) => setFeedback(data?.message ?? t("common.success")),
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {t("radar.stock_card.current_category_label", { cat: currentCategory })}
      </p>
      <Select value={selected} onValueChange={(v) => setSelected(v as StockCategory)}>
        <SelectTrigger className="text-xs h-8">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {others.map((c) => (
            <SelectItem key={c} value={c} className="text-xs">
              {CATEGORY_ICON_SHORT[c] ?? ""} {c.replace("_", " ")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button size="sm" variant="outline" onClick={handleConfirm} disabled={updateCategory.isPending}>
        {t("radar.stock_card.confirm_switch")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

function RemoveSection({ ticker }: { ticker: string }) {
  const { t } = useTranslation()
  const [reason, setReason] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)
  const deactivate = useDeactivateStock()

  const handleRemove = () => {
    if (!reason.trim()) {
      setFeedback(t("radar.stock_card.remove_reason_required"))
      return
    }
    deactivate.mutate(
      { ticker, payload: { reason: reason.trim() } },
      {
        onSuccess: (data) => setFeedback(data?.message ?? t("common.success")),
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-amber-600">{t("radar.stock_card.remove_warning")}</p>
      <textarea
        className="w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
        rows={2}
        placeholder={t("radar.stock_card.remove_reason_placeholder")}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <Button size="sm" variant="destructive" onClick={handleRemove} disabled={deactivate.isPending}>
        {t("radar.stock_card.confirm_remove")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

type TabKey = "metrics" | "thesis" | "category" | "remove"

export function StockCard({ stock, enrichment, resonance }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const [activeTab, setActiveTab] = useState<TabKey>("metrics")

  const signal = enrichment?.computed_signal ?? stock.last_scan_signal ?? "NORMAL"
  const signalIcon = SCAN_SIGNAL_ICONS[signal] ?? "⚪"
  const catIcon = CATEGORY_ICON_SHORT[stock.category] ?? ""
  const price = enrichment?.price
  const changePct = enrichment?.change_pct
  const rsi = enrichment?.rsi
  const bias = enrichment?.bias
  const marketLabel = infer_market_label(stock.ticker)
  const resonanceBadge = resonance?.length ? ` 🏆×${resonance.length}` : ""

  const headerParts = [
    `${signalIcon} ${stock.ticker}`,
    `${catIcon} ${stock.category.replace("_", " ")}`,
    price != null ? `$${price.toFixed(2)}` : null,
    changePct != null ? `(${changePct >= 0 ? "▲" : "▼"}${Math.abs(changePct).toFixed(2)}%)` : null,
    marketLabel,
    resonanceBadge || null,
  ]
    .filter(Boolean)
    .join(" · ")

  const TABS: { key: TabKey; label: string }[] = [
    { key: "metrics", label: t("radar.stock_card.signals") },
    { key: "thesis", label: t("radar.stock_card.thesis") },
    { key: "category", label: t("radar.stock_card.change_category") },
    { key: "remove", label: t("radar.stock_card.remove") },
  ]

  return (
    <Card className="border-border/70">
      <button
        className="w-full text-left p-3 font-medium text-sm hover:bg-muted/30 transition-colors rounded-t-lg"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="flex items-center justify-between">
          <span>{headerParts}</span>
          <span className="text-muted-foreground text-xs ml-2">{expanded ? "▲" : "▼"}</span>
        </span>
      </button>

      {expanded && (
        <CardContent className="pt-0 pb-3 px-3 space-y-3">
          {/* At-a-Glance metrics */}
          <div className="flex flex-wrap gap-1.5 text-xs">
            <MetricChip label="RSI" value={rsi != null ? rsi.toFixed(1) : null} color={rsi != null && rsi < 35 ? "border-green-500 text-green-600" : rsi != null && rsi > 70 ? "border-red-500 text-red-600" : undefined} />
            <MetricChip label="Bias" value={bias != null ? `${bias.toFixed(1)}%` : null} color={bias != null && bias > 20 ? "border-red-500 text-red-600" : bias != null && bias < -5 ? "border-green-500 text-green-600" : undefined} />
            {enrichment?.volume_ratio != null && (
              <MetricChip label="Vol" value={`${enrichment.volume_ratio.toFixed(1)}x`} />
            )}
          </div>

          {/* Current thesis */}
          <div className="rounded-md bg-muted/30 p-2 text-sm">
            {stock.current_thesis || <span className="text-muted-foreground italic">{t("radar.stock_card.no_thesis")}</span>}
          </div>

          {/* Tags */}
          {stock.current_tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {stock.current_tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}

          {/* Earnings & Dividend */}
          {enrichment && (
            <div className="flex gap-4 text-xs text-muted-foreground">
              {enrichment.earnings?.next_earnings_date && (
                <span>
                  📅 {t("radar.stock_card.earnings")}: {enrichment.earnings.next_earnings_date}
                  {enrichment.earnings.days_until != null && enrichment.earnings.days_until <= 14 && (
                    <span className="ml-1 text-amber-500">({enrichment.earnings.days_until}d)</span>
                  )}
                </span>
              )}
              {!SKIP_DIVIDEND_CATEGORIES.has(stock.category) && enrichment.dividend?.dividend_yield != null && (
                <span>
                  💰 {t("radar.stock_card.dividend")}: {enrichment.dividend.dividend_yield.toFixed(2)}%
                </span>
              )}
            </div>
          )}

          {/* Resonance */}
          {resonance && resonance.length > 0 && (
            <p className="text-xs text-muted-foreground">
              🏆 {resonance.map((r) => r.guru_display_name).join(", ")} ({resonance.length})
            </p>
          )}

          {/* Detail tabs */}
          <div className="border-t border-border/50 pt-2">
            <div className="flex gap-1 flex-wrap mb-2">
              {TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                    activeTab === tab.key
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="pt-1">
              {activeTab === "metrics" && (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {enrichment?.signals?.price != null && (
                      <span className="text-muted-foreground">Price: ${(enrichment.signals.price as number).toFixed(2)}</span>
                    )}
                    {enrichment?.signals?.ma200 != null && (
                      <span className="text-muted-foreground">MA200: ${(enrichment.signals.ma200 as number).toFixed(2)}</span>
                    )}
                    {enrichment?.signals?.ma60 != null && (
                      <span className="text-muted-foreground">MA60: ${(enrichment.signals.ma60 as number).toFixed(2)}</span>
                    )}
                  </div>
                  <ThesisHistorySection ticker={stock.ticker} />
                </div>
              )}
              {activeTab === "thesis" && <ThesisSection ticker={stock.ticker} stock={stock} />}
              {activeTab === "category" && <ChangeCategorySection ticker={stock.ticker} currentCategory={stock.category} />}
              {activeTab === "remove" && <RemoveSection ticker={stock.ticker} />}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}
