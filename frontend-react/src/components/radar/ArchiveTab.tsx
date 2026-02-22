import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { CATEGORY_ICON_SHORT, STOCK_CATEGORIES } from "@/lib/constants"
import { useReactivateStock, useRemovalHistory, useThesisHistory } from "@/api/hooks/useRadar"
import type { RemovedStock, StockCategory } from "@/api/types/radar"

interface RemovalHistoryProps {
  ticker: string
}

function RemovalHistorySection({ ticker }: RemovalHistoryProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: history, isLoading } = useRemovalHistory(ticker, open)

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
      >
        {open ? "▲" : "▼"} {t("radar.removed.history_title", { ticker })}
      </button>
      {open && (
        <div className="mt-2 space-y-1">
          {isLoading ? (
            <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
          ) : !history?.length ? (
            <p className="text-xs text-muted-foreground">{t("radar.removed.no_history")}</p>
          ) : (
            history.map((entry, i) => (
              <div key={i} className="rounded border border-border p-2 text-xs">
                <p className="font-semibold text-muted-foreground">{entry.created_at.slice(0, 10)}</p>
                <p>{entry.reason}</p>
              </div>
            ))
          )}
        </div>
      )}
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
        {open ? "▲" : "▼"} {t("radar.removed.thesis_history_title", { ticker })}
      </button>
      {open && (
        <div className="mt-2 space-y-1">
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
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function ReactivateSection({ ticker }: { ticker: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState<StockCategory>("Growth")
  const [thesis, setThesis] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)
  const reactivate = useReactivateStock()

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
      >
        ▼ {t("radar.removed.reactivate_title", { ticker })}
      </button>
    )
  }

  const handleConfirm = () => {
    reactivate.mutate(
      {
        ticker,
        payload: { category, thesis: thesis.trim() || undefined },
      },
      {
        onSuccess: (data) => setFeedback(data?.message ?? t("radar.removed.reactivate_success")),
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => setOpen(false)}
        className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
      >
        ▲ {t("radar.removed.reactivate_title", { ticker })}
      </button>
      <Select value={category} onValueChange={(v) => setCategory(v as StockCategory)}>
        <SelectTrigger className="text-xs h-8">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STOCK_CATEGORIES.map((c) => (
            <SelectItem key={c} value={c} className="text-xs">
              {CATEGORY_ICON_SHORT[c] ?? ""} {c.replace("_", " ")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <textarea
        className="w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
        rows={2}
        placeholder={t("radar.removed.reactivate_thesis_placeholder")}
        value={thesis}
        onChange={(e) => setThesis(e.target.value)}
      />
      <Button size="sm" onClick={handleConfirm} disabled={reactivate.isPending}>
        {t("radar.removed.reactivate_button")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

interface Props {
  removedStocks: RemovedStock[]
}

export function ArchiveTab({ removedStocks }: Props) {
  const { t } = useTranslation()

  if (!removedStocks.length) {
    return <p className="text-sm text-muted-foreground py-4">{t("radar.removed.no_removed_stocks")}</p>
  }

  return (
    <div className="space-y-3">
      {removedStocks.map((removed) => (
        <Card key={removed.ticker}>
          <CardContent className="p-4 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold">📦 {removed.ticker}</p>
                <p className="text-xs text-muted-foreground">
                  {t("radar.removed.category", { category: removed.category.replace("_", " ") })}
                  {removed.removed_at ? ` · ${t("radar.removed.date", { date: removed.removed_at.slice(0, 10) })}` : ""}
                </p>
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">{t("radar.removed.reason_title")}</p>
              <p className="text-sm rounded bg-destructive/10 border border-destructive/20 px-2 py-1">
                {removed.removal_reason || t("radar.removed.unknown")}
              </p>
            </div>

            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">{t("radar.removed.last_thesis_title")}</p>
              <p className="text-sm rounded bg-muted/30 px-2 py-1">
                {removed.current_thesis || t("radar.removed.no_thesis")}
              </p>
            </div>

            <RemovalHistorySection ticker={removed.ticker} />
            <ThesisHistorySection ticker={removed.ticker} />
            <ReactivateSection ticker={removed.ticker} />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
