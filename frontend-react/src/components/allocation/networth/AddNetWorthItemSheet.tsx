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
  initialKind?: ItemKind
}

type ItemKind = "asset" | "liability"
type LiabilityPreset = "mortgage" | "loan" | "credit_card" | "other_liability"

export function AddNetWorthItemSheet({
  open,
  onClose,
  initialKind = "asset",
}: Props) {
  const { t } = useTranslation()
  const createMutation = useCreateNetWorthItem()
  const [name, setName] = useState("")
  const [kind, setKind] = useState<ItemKind>(initialKind)
  const [category, setCategory] = useState(initialKind === "asset" ? "property" : "mortgage")
  const [value, setValue] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [interestRate, setInterestRate] = useState("")
  const [minimumPayment, setMinimumPayment] = useState("")
  const [note, setNote] = useState("")

  const categories = useMemo(
    () => (kind === "asset" ? NET_WORTH_ASSET_CATEGORIES : NET_WORTH_LIABILITY_CATEGORIES),
    [kind],
  )

  const reset = () => {
    setName("")
    setKind(initialKind)
    setCategory(initialKind === "asset" ? "property" : "mortgage")
    setValue("")
    setCurrency("USD")
    setInterestRate("")
    setMinimumPayment("")
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
        minimum_payment: minimumPayment ? Number(minimumPayment) : undefined,
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
            <label htmlFor="nw-name" className="text-xs font-medium">{t("net_worth.fields.name")}</label>
            <Input id="nw-name" value={name} onChange={(e) => setName(e.target.value)} className="text-xs" />
          </div>

          <div className="space-y-1">
            <span className="text-xs font-medium">{t("net_worth.fields.kind")}</span>
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

          {kind === "asset" ? (
            <div className="space-y-1">
              <label htmlFor="nw-category" className="text-xs font-medium">{t("net_worth.fields.category")}</label>
              <select
                id="nw-category"
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
          ) : (
            <div className="space-y-2">
              <p className="text-xs font-medium">{t("net_worth.fields.category")}</p>
              <div className="grid grid-cols-2 gap-2">
                {(NET_WORTH_LIABILITY_CATEGORIES as readonly LiabilityPreset[]).map(
                  (preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setCategory(preset)}
                      className={`rounded border px-2 py-2 text-left text-xs transition-colors ${
                        category === preset
                          ? "border-primary bg-primary/10"
                          : "border-border hover:bg-muted/40"
                      }`}
                    >
                      <p className="font-medium">{t(`net_worth.preset.${preset}`)}</p>
                      {preset !== "other_liability" && (
                        <p className="text-muted-foreground">
                          {t(`net_worth.preset.${preset}_subtitle`)}
                        </p>
                      )}
                    </button>
                  ),
                )}
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label htmlFor="nw-value" className="text-xs font-medium">
              {kind === "liability"
                ? t("net_worth.fields.outstanding_balance")
                : t("net_worth.fields.value")}
            </label>
            <Input
              id="nw-value"
              type="number"
              min={0}
              step="any"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="text-xs"
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="nw-currency" className="text-xs font-medium">{t("net_worth.fields.currency")}</label>
            <Input id="nw-currency" value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} className="text-xs" />
          </div>

          {kind === "liability" && (
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label htmlFor="nw-apr" className="text-xs font-medium">{t("net_worth.fields.apr")}</label>
                <Input
                  id="nw-apr"
                  type="number"
                  min={0}
                  step="any"
                  value={interestRate}
                  onChange={(e) => setInterestRate(e.target.value)}
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="nw-min-payment" className="text-xs font-medium">
                  {t("net_worth.fields.minimum_payment")}
                </label>
                <Input
                  id="nw-min-payment"
                  type="number"
                  min={0}
                  step="any"
                  value={minimumPayment}
                  onChange={(e) => setMinimumPayment(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label htmlFor="nw-note" className="text-xs font-medium">{t("net_worth.fields.note")}</label>
            <Input id="nw-note" value={note} onChange={(e) => setNote(e.target.value)} className="text-xs" />
          </div>

          <Button onClick={onSubmit} disabled={createMutation.isPending} className="w-full min-h-[44px]">
            {t("net_worth.add_item")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
