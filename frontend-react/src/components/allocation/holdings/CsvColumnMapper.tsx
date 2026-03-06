import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { ColumnMapping } from "@/lib/csv-import"
import { STOCK_CATEGORIES } from "@/lib/constants"

interface Props {
  headers: string[]
  mapping: ColumnMapping
  onMappingChange: (next: ColumnMapping) => void
}

const SKIP = "__skip__"

export function CsvColumnMapper({ headers, mapping, onMappingChange }: Props) {
  const { t } = useTranslation()

  const updateColumn = (key: keyof ColumnMapping, value: string) => {
    onMappingChange({
      ...mapping,
      [key]: value === SKIP ? undefined : value,
    })
  }

  const renderColumnSelect = (
    key: keyof ColumnMapping,
    labelKey: string,
    value: string | undefined,
  ) => {
    return (
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium">{t(labelKey)}</p>
          {value ? <Badge variant="secondary">{t("allocation.csv_import.auto_detected")}</Badge> : null}
        </div>
        <Select value={value ?? SKIP} onValueChange={(next) => updateColumn(key, next)}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={SKIP}>{t("allocation.csv_import.skip_column")}</SelectItem>
            {headers.map((header) => (
              <SelectItem key={header} value={header}>
                {header}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold">{t("allocation.csv_import.map_columns")}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {renderColumnSelect("tickerColumn", "allocation.csv_import.ticker", mapping.tickerColumn)}
        {renderColumnSelect("quantityColumn", "allocation.csv_import.quantity", mapping.quantityColumn)}
        {renderColumnSelect("categoryColumn", "allocation.csv_import.category", mapping.categoryColumn)}
        {renderColumnSelect("costBasisColumn", "allocation.csv_import.cost_basis", mapping.costBasisColumn)}
        {renderColumnSelect("currencyColumn", "allocation.csv_import.currency", mapping.currencyColumn)}
        {renderColumnSelect("brokerColumn", "allocation.csv_import.broker", mapping.brokerColumn)}
        {renderColumnSelect("accountTypeColumn", "allocation.csv_import.account_type", mapping.accountTypeColumn)}
        {renderColumnSelect("isCashColumn", "allocation.csv_import.is_cash", mapping.isCashColumn)}
      </div>

      <div className="space-y-2 border rounded-md p-3">
        <p className="text-sm font-medium">{t("allocation.csv_import.use_default")}</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{t("allocation.csv_import.category")}</p>
            <Select
              value={mapping.categoryDefault ?? "Growth"}
              onValueChange={(value) =>
                onMappingChange({ ...mapping, categoryDefault: value as ColumnMapping["categoryDefault"] })
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STOCK_CATEGORIES.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{t("allocation.csv_import.currency")}</p>
            <Input
              value={mapping.currencyDefault ?? "USD"}
              onChange={(e) =>
                onMappingChange({
                  ...mapping,
                  currencyDefault: e.target.value.trim().toUpperCase() || "USD",
                })
              }
              maxLength={3}
            />
          </div>

          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">{t("allocation.csv_import.broker")}</p>
            <Input
              value={mapping.brokerDefault ?? ""}
              onChange={(e) => onMappingChange({ ...mapping, brokerDefault: e.target.value })}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
