import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { useDeleteNetWorthItem, useUpdateNetWorthItem } from "@/api/hooks/useNetWorth"
import { formatPrice } from "@/lib/format"
import type { NetWorthItemResponse } from "@/api/types/networth"

interface Props {
  items: NetWorthItemResponse[]
  privacyMode: boolean
}

export function NetWorthItemsTable({ items, privacyMode }: Props) {
  const { t } = useTranslation()
  const updateMutation = useUpdateNetWorthItem()
  const deleteMutation = useDeleteNetWorthItem()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingValue, setEditingValue] = useState("")
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const startEdit = (item: NetWorthItemResponse) => {
    setEditingId(item.id)
    setEditingValue(String(item.value))
  }

  const saveEdit = (id: number) => {
    const parsed = Number(editingValue)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      toast.error(t("common.error"))
      return
    }
    updateMutation.mutate(
      { id, payload: { value: parsed } },
      {
        onSuccess: () => {
          setEditingId(null)
          toast.success(t("common.success"))
        },
        onError: () => toast.error(t("common.error")),
      },
    )
  }

  const onDelete = (id: number) => {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        setDeleteId(null)
        toast.success(t("common.success"))
      },
      onError: () => toast.error(t("common.error")),
    })
  }

  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("net_worth.empty")}</p>
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold">{t("net_worth.items_title")}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-1 pr-2">{t("net_worth.fields.name")}</th>
              <th className="text-left py-1 pr-2">{t("net_worth.fields.category")}</th>
              <th className="text-right py-1 pr-2">{t("net_worth.fields.value")}</th>
              <th className="text-left py-1 pr-2">{t("net_worth.fields.currency")}</th>
              <th className="text-left py-1 pr-2">{t("common.warning")}</th>
              <th className="text-right py-1">{t("common.edit")}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-border/50">
                <td className="py-1 pr-2">{item.name}</td>
                <td className="py-1 pr-2">{t(`net_worth.categories.${item.category}`)}</td>
                <td className="py-1 pr-2 text-right">
                  {editingId === item.id ? (
                    <Input
                      type="number"
                      min={0}
                      step="any"
                      value={editingValue}
                      onChange={(e) => setEditingValue(e.target.value)}
                      className="h-7 w-24 text-xs text-right"
                    />
                  ) : (
                    <>{privacyMode ? "***" : formatPrice(item.value, item.currency)}</>
                  )}
                </td>
                <td className="py-1 pr-2">{item.currency}</td>
                <td className="py-1 pr-2 text-muted-foreground">
                  {item.is_stale ? t("net_worth.last_updated_days", { days: item.days_since_update }) : "—"}
                </td>
                <td className="py-1 text-right whitespace-nowrap">
                  {editingId === item.id ? (
                    <>
                      <button
                        onClick={() => saveEdit(item.id)}
                        className="text-primary hover:underline mr-2"
                        disabled={updateMutation.isPending}
                      >
                        {t("common.save")}
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="text-muted-foreground hover:underline"
                      >
                        {t("common.cancel")}
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => startEdit(item)} className="text-primary hover:underline mr-2">
                        {t("common.edit")}
                      </button>
                      {deleteId === item.id ? (
                        <>
                          <button
                            onClick={() => onDelete(item.id)}
                            className="text-destructive hover:underline mr-2"
                            disabled={deleteMutation.isPending}
                          >
                            {t("common.confirm")}
                          </button>
                          <button
                            onClick={() => setDeleteId(null)}
                            className="text-muted-foreground hover:underline"
                          >
                            {t("common.cancel")}
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setDeleteId(item.id)}
                          className="text-destructive hover:underline"
                        >
                          {t("common.delete")}
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
