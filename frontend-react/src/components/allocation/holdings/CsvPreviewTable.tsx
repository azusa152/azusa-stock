import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { CsvParseWarning, HoldingImportItem, ValidationError } from "@/lib/csv-import"

interface Props {
  items: HoldingImportItem[]
  errors: Map<number, ValidationError[]>
  parseWarnings?: CsvParseWarning[]
}

export function CsvPreviewTable({ items, errors, parseWarnings = [] }: Props) {
  const { t } = useTranslation()
  const previewItems = items.slice(0, 10)
  const invalidCount = errors.size
  const validCount = items.length - invalidCount

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold">{t("allocation.csv_import.preview_title")}</p>
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span>{t("allocation.csv_import.total_rows", { count: items.length })}</span>
        <span>{t("allocation.csv_import.valid_rows", { count: validCount })}</span>
        <span>{t("allocation.csv_import.error_rows", { count: invalidCount })}</span>
        {parseWarnings.length > 0 ? (
          <span>{t("allocation.csv_import.parse_warnings", { count: parseWarnings.length })}</span>
        ) : null}
      </div>

      {parseWarnings.length > 0 ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          <p className="font-medium">{t("allocation.csv_import.parse_warnings_title")}</p>
          <ul className="mt-1 list-disc pl-4">
            {parseWarnings.slice(0, 5).map((warning, idx) => (
              <li key={`${warning.code}-${warning.row}-${idx}`}>
                {t("allocation.csv_import.parse_warning_item", {
                  row: warning.row >= 0 ? warning.row + 1 : "-",
                  code: warning.code,
                  message: warning.message,
                })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="max-h-72 overflow-auto rounded-md border">
        <table className="w-full text-xs">
          <thead className="bg-muted/40 sticky top-0">
            <tr>
              <th className="text-left px-2 py-2">#</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.ticker")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.category")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.quantity")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.cost_basis")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.currency")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.broker")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.account_type")}</th>
              <th className="text-left px-2 py-2">{t("allocation.csv_import.status")}</th>
            </tr>
          </thead>
          <tbody>
            {previewItems.map((item, idx) => {
              const rowErrors = errors.get(idx) ?? []
              return (
                <tr key={`${item.ticker}-${idx}`} className="border-t align-top">
                  <td className="px-2 py-2">{idx + 1}</td>
                  <td className="px-2 py-2">{item.ticker}</td>
                  <td className="px-2 py-2">{item.category}</td>
                  <td className="px-2 py-2">{item.quantity}</td>
                  <td className="px-2 py-2">{item.cost_basis ?? "-"}</td>
                  <td className="px-2 py-2">{item.currency}</td>
                  <td className="px-2 py-2">{item.broker ?? "-"}</td>
                  <td className="px-2 py-2">{item.account_type ?? "-"}</td>
                  <td className="px-2 py-2">
                    {rowErrors.length === 0 ? (
                      <span className="inline-flex items-center gap-1 text-emerald-600">
                        <CheckCircle2 className="size-3" />
                        {t("common.success")}
                      </span>
                    ) : (
                      <div className="text-destructive">
                        <span className="inline-flex items-center gap-1">
                          <AlertTriangle className="size-3" />
                          {rowErrors.length}
                        </span>
                        <ul className="mt-1 space-y-0.5">
                          {rowErrors.map((error) => (
                            <li key={error.code}>{error.message}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
