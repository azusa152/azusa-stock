import { useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useImportHoldings } from "@/api/hooks/useAllocation"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { CsvColumnMapper } from "@/components/allocation/holdings/CsvColumnMapper"
import { CsvPreviewTable } from "@/components/allocation/holdings/CsvPreviewTable"
import {
  autoDetectColumns,
  parseCSV,
  isCashRow,
  transformRows,
  validateRows,
  type CsvParseWarning,
  type ColumnMapping,
  type CsvRow,
} from "@/lib/csv-import"

interface Props {
  open: boolean
  onClose: () => void
}

type Step = "select" | "map" | "preview"

const TEMPLATE_URL = "/templates/holdings_csv_template.csv"

export function CsvImportDialog({ open, onClose }: Props) {
  const { t } = useTranslation()
  const importMutation = useImportHoldings()
  const fileRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<Step>("select")
  const [headers, setHeaders] = useState<string[]>([])
  const [rows, setRows] = useState<CsvRow[]>([])
  const [mapping, setMapping] = useState<ColumnMapping>({
    categoryDefault: "Growth",
    currencyDefault: "USD",
  })
  const [feedback, setFeedback] = useState<string | null>(null)
  const [parseWarnings, setParseWarnings] = useState<CsvParseWarning[]>([])
  const [replaceAllConfirmed, setReplaceAllConfirmed] = useState(false)

  const items = useMemo(() => transformRows(rows, mapping), [rows, mapping])
  const errors = useMemo(() => validateRows(items), [items])
  const hasBlockingErrors = errors.size > 0
  const hasNoRowsToImport = items.length === 0

  const reset = () => {
    setStep("select")
    setHeaders([])
    setRows([])
    setFeedback(null)
    setParseWarnings([])
    setReplaceAllConfirmed(false)
    setMapping({ categoryDefault: "Growth", currencyDefault: "USD" })
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const parsed = await parseCSV(file)
      if (!parsed.headers.length) {
        setFeedback(t("allocation.csv_import.missing_headers"))
        return
      }
      setHeaders(parsed.headers)
      setRows(parsed.rows)
      setParseWarnings(parsed.warnings)
      setMapping((prev) => ({ ...autoDetectColumns(parsed.headers), categoryDefault: prev.categoryDefault ?? "Growth", currencyDefault: prev.currencyDefault ?? "USD" }))
      setFeedback(null)
      setStep("map")
    } catch {
      setFeedback(t("allocation.csv_import.parse_error"))
    } finally {
      e.target.value = ""
    }
  }

  const validateRequiredMappings = () => {
    if (!mapping.quantityColumn) {
      setFeedback(t("allocation.csv_import.missing_required_mapping_quantity"))
      return false
    }
    if (!mapping.categoryColumn && !mapping.categoryDefault) {
      setFeedback(t("allocation.csv_import.missing_required_mapping_category"))
      return false
    }
    const hasNonCashRows = items.some((item) => !isCashRow(item))
    if (hasNonCashRows && !mapping.tickerColumn) {
      setFeedback(t("allocation.csv_import.missing_required_mapping_ticker_non_cash"))
      return false
    }
    return true
  }

  const goToPreview = () => {
    if (!validateRequiredMappings()) return
    setFeedback(null)
    setStep("preview")
  }

  const handleImport = () => {
    if (hasBlockingErrors) return
    if (hasNoRowsToImport) {
      setFeedback(t("allocation.csv_import.no_rows_to_import"))
      return
    }
    if (!replaceAllConfirmed) {
      setFeedback(t("allocation.csv_import.confirm_replace_all_required"))
      return
    }
    importMutation.mutate(items, {
      onSuccess: () => {
        toast.success(t("allocation.csv_import.import_success"))
        handleClose()
      },
      onError: () => {
        const message = t("allocation.csv_import.import_error")
        setFeedback(message)
        toast.error(message)
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && handleClose()}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>{t("allocation.csv_import.title")}</DialogTitle>
          <DialogDescription>{t("allocation.csv_import.description")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            {step === "select" && t("allocation.csv_import.step_select")}
            {step === "map" && t("allocation.csv_import.step_map")}
            {step === "preview" && t("allocation.csv_import.step_preview")}
          </p>

          {step === "select" && (
            <div className="space-y-3">
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.tsv,text/csv,text/tab-separated-values"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="flex gap-2">
                <Button type="button" onClick={() => fileRef.current?.click()}>
                  {t("allocation.csv_import.select_file")}
                </Button>
                <Button asChild variant="outline">
                  <a href={TEMPLATE_URL} download>
                    {t("allocation.csv_import.download_template")}
                  </a>
                </Button>
              </div>
            </div>
          )}

          {step === "map" && (
            <CsvColumnMapper headers={headers} mapping={mapping} onMappingChange={setMapping} />
          )}

          {step === "preview" && (
            <div className="space-y-3">
              <CsvPreviewTable items={items} errors={errors} parseWarnings={parseWarnings} />
              <div className="flex items-start gap-2 rounded-md border p-3">
                <input
                  id="replace-all-confirm"
                  type="checkbox"
                  checked={replaceAllConfirmed}
                  onChange={(event) => setReplaceAllConfirmed(event.target.checked)}
                  className="mt-0.5 h-4 w-4"
                />
                <label htmlFor="replace-all-confirm" className="text-sm leading-5">
                  {t("allocation.csv_import.replace_all_confirm")}
                </label>
              </div>
            </div>
          )}

          {feedback ? <p className="text-sm text-destructive">{feedback}</p> : null}
        </div>

        <DialogFooter>
          {step !== "select" ? (
            <Button type="button" variant="outline" onClick={() => setStep(step === "preview" ? "map" : "select")}>
              {t("allocation.csv_import.back")}
            </Button>
          ) : null}
          {step === "select" ? (
            <Button type="button" variant="outline" onClick={handleClose}>
              {t("allocation.csv_import.close")}
            </Button>
          ) : null}
          {step === "map" ? (
            <Button type="button" onClick={goToPreview}>
              {t("allocation.csv_import.next")}
            </Button>
          ) : null}
          {step === "preview" ? (
            <Button
              type="button"
              onClick={handleImport}
              disabled={hasBlockingErrors || importMutation.isPending || hasNoRowsToImport || !replaceAllConfirmed}
            >
              {t("allocation.csv_import.confirm_import", { count: items.length })}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
