import { useEffect, useRef, useState } from "react"
import axios from "axios"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { useHoldings } from "@/api/hooks/useDashboard"
import { useUpdateHolding, useDeleteHolding } from "@/api/hooks/useAllocation"
import type { Holding } from "@/api/types/allocation"
import { formatPrice } from "@/lib/format"

interface Props {
  privacyMode: boolean
}

interface EditState {
  id: number
  quantity: string
  cost_basis: string
  broker: string
  error: string | null
}

export function HoldingsManager({ privacyMode }: Props) {
  const { t } = useTranslation()
  const { data: holdings } = useHoldings()
  const updateMutation = useUpdateHolding()
  const deleteMutation = useDeleteHolding()

  const [editing, setEditing] = useState<EditState | null>(null)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const quantityRef = useRef<HTMLInputElement>(null)

  // Focus the first editable input when entering edit mode.
  // Keyed on editingId (not the full editing object) so focus only fires when the
  // row changes, not on every field keystroke.
  const editingId = editing?.id ?? null
  useEffect(() => {
    if (editingId !== null) {
      quantityRef.current?.focus()
    }
  }, [editingId])

  const startEdit = (h: Holding) => {
    setEditing({
      id: h.id,
      quantity: String(h.quantity),
      cost_basis: h.cost_basis != null ? String(h.cost_basis) : "",
      broker: h.broker ?? "",
      error: null,
    })
    setDeleteId(null)
  }

  const validateAndSave = () => {
    if (!editing) return

    const qty = Number(editing.quantity)
    if (!editing.quantity || isNaN(qty) || qty <= 0) {
      setEditing((prev) => prev ? { ...prev, error: t("allocation.manager.err_qty") } : prev)
      return
    }
    const costBasis = editing.cost_basis !== "" ? Number(editing.cost_basis) : undefined
    if (costBasis !== undefined && (isNaN(costBasis) || costBasis < 0)) {
      setEditing((prev) => prev ? { ...prev, error: t("allocation.manager.err_cost") } : prev)
      return
    }

    setEditing((prev) => prev ? { ...prev, error: null } : prev)
    updateMutation.mutate(
      {
        id: editing.id,
        payload: {
          quantity: qty,
          cost_basis: costBasis,
          broker: editing.broker || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success(t("common.success"))
          setEditing(null)
        },
        onError: (err: unknown) => {
          const msg = axios.isAxiosError(err)
            ? (err.response?.data?.detail ?? t("common.error"))
            : t("common.error")
          setEditing((prev) => prev ? { ...prev, error: msg } : prev)
          toast.error(msg)
        },
      },
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") validateAndSave()
    if (e.key === "Escape") setEditing(null)
  }

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        setDeleteId(null)
        toast.success(t("common.success"))
      },
      onError: () => {
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

      {editing && (
        <p className="text-xs text-muted-foreground">
          {t("allocation.manager.edit_hint")}
        </p>
      )}

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
                <tr
                  key={h.id}
                  className="border-b border-primary/40 bg-primary/5 ring-1 ring-inset ring-primary/20"
                >
                  <td className="py-1.5 pr-2 font-semibold text-primary">{h.ticker}</td>
                  <td className="py-1.5 pr-2 text-muted-foreground">{h.category}</td>
                  <td className="py-1 pr-2">
                    <Input
                      ref={quantityRef}
                      value={editing.quantity}
                      onChange={(e) =>
                        setEditing((prev) => prev ? { ...prev, quantity: e.target.value, error: null } : prev)
                      }
                      onKeyDown={handleKeyDown}
                      type="number"
                      min={0}
                      step="any"
                      aria-label={t("allocation.col.qty")}
                      className="text-xs h-6 w-24 text-right"
                    />
                  </td>
                  <td className="py-1 pr-2">
                    <Input
                      value={editing.cost_basis}
                      onChange={(e) =>
                        setEditing((prev) => prev ? { ...prev, cost_basis: e.target.value, error: null } : prev)
                      }
                      onKeyDown={handleKeyDown}
                      type="number"
                      min={0}
                      step="any"
                      aria-label={t("allocation.col.cost")}
                      className="text-xs h-6 w-24 text-right"
                      placeholder="—"
                    />
                  </td>
                  <td className="py-1 pr-2">
                    <Input
                      value={editing.broker}
                      onChange={(e) =>
                        setEditing((prev) => prev ? { ...prev, broker: e.target.value } : prev)
                      }
                      onKeyDown={handleKeyDown}
                      aria-label={t("allocation.manager.col_broker")}
                      className="text-xs h-6 w-28"
                      placeholder="—"
                    />
                  </td>
                  <td className="py-1 text-right space-x-1 whitespace-nowrap">
                    <button
                      onClick={validateAndSave}
                      className="text-xs text-primary hover:underline disabled:opacity-50"
                      disabled={updateMutation.isPending}
                    >
                      {updateMutation.isPending ? t("common.saving") : t("common.save")}
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
                <tr key={h.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.category}</td>
                  <td className="py-0.5 pr-2 text-right">{privacyMode ? "***" : h.quantity}</td>
                  <td className="py-0.5 pr-2 text-right">
                    {privacyMode ? "***" : (h.cost_basis != null ? formatPrice(h.cost_basis, h.currency) : "—")}
                  </td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.broker ?? "—"}</td>
                  <td className="py-0.5 text-right space-x-2 whitespace-nowrap">
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

      {editing?.error && (
        <p className="text-xs text-destructive">{editing.error}</p>
      )}
    </div>
  )
}
