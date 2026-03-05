import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { NET_WORTH_ASSET_CATEGORIES, NET_WORTH_LIABILITY_CATEGORIES } from "@/lib/constants"
import { useCreateNetWorthItem } from "@/api/hooks/useNetWorth"

interface Props {
  open: boolean
  onClose: () => void
}

type ItemKind = "asset" | "liability"

export function AddNetWorthItemSheet({ open, onClose }: Props) {
  const { t } = useTranslation()
  const createMutation = useCreateNetWorthItem()
  const [name, setName] = useState("")
  const [kind, setKind] = useState<ItemKind>("asset")
  const [category, setCategory] = useState("property")
  const [value, setValue] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [interestRate, setInterestRate] = useState("")
  const [note, setNote] = useState("")

  const categories = useMemo(
    () => (kind === "asset" ? NET_WORTH_ASSET_CATEGORIES : NET_WORTH_LIABILITY_CATEGORIES),
    [kind],
  )

  const reset = () => {
    setName("")
    setKind("asset")
    setCategory("property")
    setValue("")
    setCurrency("USD")
    setInterestRate("")
    setNote("")
  }

  const onSubmit = () => {
    const parsed = Number(value)
    if (!name.trim() || !Number.isFinite(parsed) || parsed <= 0) {
      toast.error(t("common.error"))
      return
    }
    createMutation.mutate(
      {
        name: name.trim(),
        kind,
        category,
        value: parsed,
        currency,
        interest_rate: interestRate ? Number(interestRate) : undefined,
        note: note.trim() || null,
      },
      {
        onSuccess: () => {
          toast.success(t("common.success"))
          reset()
          onClose()
        },
        onError: () => toast.error(t("common.error")),
      },
    )
  }

  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("net_worth.add_item")}</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-3">
          <div className="space-y-1">
            <p className="text-xs font-medium">{t("net_worth.fields.name")}</p>
            <Input value={name} onChange={(e) => setName(e.target.value)} className="text-xs" />
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("net_worth.fields.kind")}</p>
            <div className="flex gap-2">
              <Button
                type="button"
                size="sm"
                variant={kind === "asset" ? "default" : "outline"}
                onClick={() => {
                  setKind("asset")
                  setCategory("property")
                }}
                className="text-xs"
              >
                {t("net_worth.kind.asset")}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={kind === "liability" ? "default" : "outline"}
                onClick={() => {
                  setKind("liability")
                  setCategory("mortgage")
                }}
                className="text-xs"
              >
                {t("net_worth.kind.liability")}
              </Button>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("net_worth.fields.category")}</p>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded border border-border bg-background px-3 py-2 text-xs min-h-[40px]"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {t(`net_worth.categories.${cat}`)}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("net_worth.fields.value")}</p>
            <Input
              type="number"
              min={0}
              step="any"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="text-xs"
            />
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("net_worth.fields.currency")}</p>
            <Input value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} className="text-xs" />
          </div>

          {kind === "liability" && (
            <div className="space-y-1">
              <p className="text-xs font-medium">{t("net_worth.fields.interest_rate")}</p>
              <Input
                type="number"
                min={0}
                step="any"
                value={interestRate}
                onChange={(e) => setInterestRate(e.target.value)}
                className="text-xs"
              />
            </div>
          )}

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("net_worth.fields.note")}</p>
            <Input value={note} onChange={(e) => setNote(e.target.value)} className="text-xs" />
          </div>

          <Button onClick={onSubmit} disabled={createMutation.isPending} className="w-full min-h-[44px]">
            {t("net_worth.add_item")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
