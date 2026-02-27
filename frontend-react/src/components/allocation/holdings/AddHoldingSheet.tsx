import { useState, useRef } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useAddHolding, useAddCashHolding, useImportHoldings } from "@/api/hooks/useAllocation"
import { useHoldings } from "@/api/hooks/useDashboard"
import { STOCK_CATEGORIES, DISPLAY_CURRENCIES, ACCOUNT_TYPES } from "@/lib/constants"
import type { StockCategory } from "@/api/types/allocation"
import type { components } from "@/api/types/generated"

interface Props {
  open: boolean
  onClose: () => void
}

type AssetType = "stock" | "bond" | "cash"

export function AddHoldingSheet({ open, onClose }: Props) {
  const { t } = useTranslation()
  const fileRef = useRef<HTMLInputElement>(null)

  const [assetType, setAssetType] = useState<AssetType>("stock")
  const [ticker, setTicker] = useState("")
  const [category, setCategory] = useState<StockCategory>("Growth")
  const [quantity, setQuantity] = useState("")
  const [avgCost, setAvgCost] = useState("")
  const [broker, setBroker] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [cashAmount, setCashAmount] = useState("")
  const [cashBank, setCashBank] = useState("")
  const [cashAccountType, setCashAccountType] = useState("")

  const [feedback, setFeedback] = useState<string | null>(null)
  const [importFeedback, setImportFeedback] = useState<string | null>(null)
  const [pendingImport, setPendingImport] = useState<
    components["schemas"]["HoldingImportItem"][] | null
  >(null)

  const addHoldingMutation = useAddHolding()
  const addCashMutation = useAddCashHolding()
  const importMutation = useImportHoldings()
  const { data: holdings } = useHoldings()

  const resetForm = () => {
    setTicker("")
    setQuantity("")
    setAvgCost("")
    setBroker("")
    setCashAmount("")
    setCashBank("")
    setCashAccountType("")
    setFeedback(null)
  }

  const handleSubmitStock = () => {
    if (!ticker.trim()) {
      setFeedback(t("allocation.sidebar.error_ticker"))
      return
    }
    if (!quantity.trim() || isNaN(Number(quantity))) {
      setFeedback(t("allocation.sidebar.error_quantity"))
      return
    }
    setFeedback(null)
    addHoldingMutation.mutate(
      {
        ticker: ticker.trim().toUpperCase(),
        category,
        quantity: Number(quantity),
        cost_basis: avgCost ? Number(avgCost) : undefined,
        broker: broker || undefined,
        currency,
      },
      {
        onSuccess: () => {
          setFeedback(t("allocation.sidebar.added", { ticker: ticker.trim().toUpperCase() }))
          toast.success(t("allocation.sidebar.added", { ticker: ticker.trim().toUpperCase() }))
          resetForm()
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      },
    )
  }

  const handleSubmitBond = () => {
    if (!ticker.trim()) {
      setFeedback(t("allocation.sidebar.error_bond_ticker"))
      return
    }
    if (!quantity.trim() || isNaN(Number(quantity))) {
      setFeedback(t("allocation.sidebar.error_quantity"))
      return
    }
    setFeedback(null)
    addHoldingMutation.mutate(
      {
        ticker: ticker.trim().toUpperCase(),
        category: "Bond",
        quantity: Number(quantity),
        cost_basis: avgCost ? Number(avgCost) : undefined,
        broker: broker || undefined,
        currency,
      },
      {
        onSuccess: () => {
          setFeedback(t("allocation.sidebar.added", { ticker: ticker.trim().toUpperCase() }))
          toast.success(t("allocation.sidebar.added", { ticker: ticker.trim().toUpperCase() }))
          resetForm()
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      },
    )
  }

  const handleSubmitCash = () => {
    if (!cashAmount.trim() || isNaN(Number(cashAmount))) {
      setFeedback(t("allocation.sidebar.error_cash_amount"))
      return
    }
    setFeedback(null)
    addCashMutation.mutate(
      {
        currency,
        amount: Number(cashAmount),
        broker: cashBank || undefined,
        account_type: cashAccountType || undefined,
      },
      {
        onSuccess: () => {
          setFeedback(t("allocation.sidebar.cash_added", { label: currency, amount: cashAmount }))
          toast.success(t("allocation.sidebar.cash_added", { label: currency, amount: cashAmount }))
          resetForm()
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      },
    )
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string)
        if (!Array.isArray(parsed)) {
          setImportFeedback(t("allocation.sidebar.import_error_format"))
          return
        }
        setPendingImport(parsed as components["schemas"]["HoldingImportItem"][])
        setImportFeedback(t("allocation.sidebar.import_detected", { count: parsed.length }))
      } catch {
        setImportFeedback(t("allocation.sidebar.import_error_json"))
      }
    }
    reader.readAsText(file)
  }

  const handleImportConfirm = () => {
    if (!pendingImport) return
    importMutation.mutate(pendingImport, {
      onSuccess: () => {
        setImportFeedback(t("allocation.sidebar.import_success"))
        toast.success(t("allocation.sidebar.import_success"))
        setPendingImport(null)
      },
      onError: () => {
        setImportFeedback(t("common.error"))
        toast.error(t("common.error"))
      },
    })
  }

  const handleExport = async () => {
    try {
      const headers: HeadersInit = {}
      const apiKey = import.meta.env.VITE_API_KEY
      if (apiKey) headers["X-API-Key"] = apiKey

      const response = await fetch("/api/holdings/export", { headers })
      if (!response.ok) throw new Error(response.statusText)

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = "holdings.json"
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(t("common.error"))
    }
  }

  const inHoldings = ticker
    ? holdings?.some((h) => h.ticker.toUpperCase() === ticker.trim().toUpperCase())
    : false

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("allocation.sidebar.header")}</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          {/* Asset type toggle */}
          <div className="space-y-1">
            <p className="text-xs font-medium">{t("allocation.sidebar.asset_type")}</p>
            <div className="flex gap-1">
              {(["stock", "bond", "cash"] as AssetType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => { setAssetType(type); resetForm() }}
                  className={`flex-1 text-xs py-1 rounded border transition-colors ${
                    assetType === type
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border hover:bg-muted/30"
                  }`}
                >
                  {t(`allocation.sidebar.asset_${type}`)}
                </button>
              ))}
            </div>
          </div>

          {/* Stock form */}
          {assetType === "stock" && (
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.stock_ticker")}</p>
                <Input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  placeholder="e.g. AAPL"
                  className="text-xs"
                />
                {ticker && (
                  <p className="text-xs text-muted-foreground">
                    {inHoldings
                      ? t("allocation.sidebar.in_radar", { category })
                      : t("allocation.sidebar.not_in_radar")}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.category")}</p>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as StockCategory)}
                  className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                >
                  {STOCK_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.quantity")}</p>
                <Input value={quantity} onChange={(e) => setQuantity(e.target.value)} type="number" className="text-xs" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.avg_cost")}</p>
                <Input value={avgCost} onChange={(e) => setAvgCost(e.target.value)} type="number" className="text-xs" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.broker_optional")}</p>
                <Input
                  value={broker}
                  onChange={(e) => setBroker(e.target.value)}
                  placeholder={t("allocation.sidebar.broker_placeholder")}
                  className="text-xs"
                />
              </div>
              <Button
                onClick={handleSubmitStock}
                disabled={addHoldingMutation.isPending}
                className="w-full"
                size="sm"
              >
                {t("allocation.sidebar.add_button")}
              </Button>
            </div>
          )}

          {/* Bond form */}
          {assetType === "bond" && (
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.bond_ticker")}</p>
                <Input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  placeholder="e.g. TLT"
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.currency_label")}</p>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                >
                  {DISPLAY_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.quantity")}</p>
                <Input value={quantity} onChange={(e) => setQuantity(e.target.value)} type="number" className="text-xs" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.avg_cost")}</p>
                <Input value={avgCost} onChange={(e) => setAvgCost(e.target.value)} type="number" className="text-xs" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.broker_optional")}</p>
                <Input
                  value={broker}
                  onChange={(e) => setBroker(e.target.value)}
                  placeholder={t("allocation.sidebar.broker_placeholder")}
                  className="text-xs"
                />
              </div>
              <Button
                onClick={handleSubmitBond}
                disabled={addHoldingMutation.isPending}
                className="w-full"
                size="sm"
              >
                {t("allocation.sidebar.add_button")}
              </Button>
            </div>
          )}

          {/* Cash form */}
          {assetType === "cash" && (
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.currency_label")}</p>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                >
                  {DISPLAY_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.cash_amount")}</p>
                <Input value={cashAmount} onChange={(e) => setCashAmount(e.target.value)} type="number" className="text-xs" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.cash_bank")}</p>
                <Input
                  value={cashBank}
                  onChange={(e) => setCashBank(e.target.value)}
                  placeholder={t("allocation.sidebar.cash_bank_placeholder")}
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("allocation.sidebar.cash_account_type")}</p>
                <select
                  value={cashAccountType}
                  onChange={(e) => setCashAccountType(e.target.value)}
                  className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                >
                  <option value="">{t("allocation.sidebar.not_specified")}</option>
                  {ACCOUNT_TYPES.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>
              <Button
                onClick={handleSubmitCash}
                disabled={addCashMutation.isPending}
                className="w-full"
                size="sm"
              >
                {t("allocation.sidebar.add_button")}
              </Button>
            </div>
          )}

          {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}

          <hr className="border-border" />

          {/* Export */}
          <div className="space-y-2">
            <p className="text-xs font-semibold">{t("allocation.sidebar.export_title")}</p>
            <p className="text-xs text-muted-foreground">
              {t("allocation.sidebar.export_count", { count: holdings?.length ?? 0 })}
            </p>
            <Button size="sm" variant="outline" className="w-full text-xs" onClick={handleExport}>
              {t("allocation.sidebar.download_json")}
            </Button>
          </div>

          <hr className="border-border" />

          {/* Import */}
          <div className="space-y-2">
            <p className="text-xs font-semibold">{t("allocation.sidebar.import_title")}</p>
            <input
              ref={fileRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button
              size="sm"
              variant="outline"
              className="w-full text-xs"
              onClick={() => fileRef.current?.click()}
            >
              {t("allocation.sidebar.upload_json")}
            </Button>
            {importFeedback && <p className="text-xs text-muted-foreground">{importFeedback}</p>}
            {pendingImport && (
              <Button
                size="sm"
                className="w-full text-xs"
                onClick={handleImportConfirm}
                disabled={importMutation.isPending}
              >
                {t("allocation.sidebar.import_confirm")}
              </Button>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
