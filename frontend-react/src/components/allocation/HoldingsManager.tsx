import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { useHoldings } from "@/api/hooks/useDashboard"
import { useUpdateHolding, useDeleteHolding } from "@/api/hooks/useAllocation"
import type { Holding } from "@/api/types/allocation"

interface Props {
  privacyMode: boolean
}

interface EditState {
  id: number
  quantity: string
  cost_basis: string
  broker: string
}

export function HoldingsManager({ privacyMode }: Props) {
  const { t } = useTranslation()
  const { data: holdings } = useHoldings()
  const updateMutation = useUpdateHolding()
  const deleteMutation = useDeleteHolding()

  const [editing, setEditing] = useState<EditState | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  const startEdit = (h: Holding) => {
    setEditing({
      id: h.id,
      quantity: String(h.quantity),
      cost_basis: h.cost_basis != null ? String(h.cost_basis) : "",
      broker: h.broker ?? "",
    })
  }

  const handleSave = () => {
    if (!editing) return
    setFeedback(null)
    updateMutation.mutate(
      {
        id: editing.id,
        payload: {
          quantity: editing.quantity ? Number(editing.quantity) : undefined,
          cost_basis: editing.cost_basis ? Number(editing.cost_basis) : undefined,
          broker: editing.broker || undefined,
        },
      },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          toast.success(t("common.success"))
          setEditing(null)
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      },
    )
  }

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        setDeleteId(null)
        setFeedback(t("common.success"))
        toast.success(t("common.success"))
      },
      onError: () => {
        setFeedback(t("common.error"))
        toast.error(t("common.error"))
      },
    })
  }

  if (!holdings || holdings.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.manager.title")}</p>
        <p className="text-sm text-muted-foreground">{t("allocation.holdings.empty")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold">{t("allocation.manager.title")}</p>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.qty")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.cost")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.manager.col_broker")}</th>
              <th className="text-right py-0.5">{t("allocation.manager.col_actions")}</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) =>
              editing?.id === h.id ? (
                <tr key={h.id} className="border-b border-border/50 bg-muted/20">
                  <td className="py-1 pr-2 font-medium">{h.ticker}</td>
                  <td className="py-1 pr-2 text-muted-foreground">{h.category}</td>
                  <td className="py-1 pr-2">
                    <Input
                      value={editing.quantity}
                      onChange={(e) => setEditing((prev) => prev ? { ...prev, quantity: e.target.value } : prev)}
                      type="number"
                      className="text-xs h-6 w-20 text-right"
                    />
                  </td>
                  <td className="py-1 pr-2">
                    <Input
                      value={editing.cost_basis}
                      onChange={(e) => setEditing((prev) => prev ? { ...prev, cost_basis: e.target.value } : prev)}
                      type="number"
                      className="text-xs h-6 w-20 text-right"
                      placeholder="—"
                    />
                  </td>
                  <td className="py-1 pr-2">
                    <Input
                      value={editing.broker}
                      onChange={(e) => setEditing((prev) => prev ? { ...prev, broker: e.target.value } : prev)}
                      className="text-xs h-6 w-24"
                      placeholder="—"
                    />
                  </td>
                  <td className="py-1 text-right space-x-1">
                    <button
                      onClick={handleSave}
                      className="text-xs text-primary hover:underline"
                      disabled={updateMutation.isPending}
                    >
                      {t("common.save")}
                    </button>
                    <button
                      onClick={() => setEditing(null)}
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      {t("common.cancel")}
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={h.id} className="border-b border-border/50">
                  <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.category}</td>
                  <td className="py-0.5 pr-2 text-right">{privacyMode ? "***" : h.quantity}</td>
                  <td className="py-0.5 pr-2 text-right">
                    {privacyMode ? "***" : (h.cost_basis != null ? h.cost_basis.toFixed(2) : "—")}
                  </td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.broker ?? "—"}</td>
                  <td className="py-0.5 text-right space-x-2">
                    <button
                      onClick={() => startEdit(h)}
                      className="text-xs text-primary hover:underline"
                    >
                      {t("allocation.manager.edit_button")}
                    </button>
                    {deleteId === h.id ? (
                      <>
                        <button
                          onClick={() => handleDelete(h.id)}
                          className="text-xs text-destructive hover:underline"
                          disabled={deleteMutation.isPending}
                        >
                          {t("common.confirm")}
                        </button>
                        <button
                          onClick={() => setDeleteId(null)}
                          className="text-xs text-muted-foreground hover:underline"
                        >
                          {t("common.cancel")}
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => setDeleteId(h.id)}
                        className="text-xs text-destructive hover:underline"
                      >
                        {t("allocation.manager.delete_button")}
                      </button>
                    )}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}
