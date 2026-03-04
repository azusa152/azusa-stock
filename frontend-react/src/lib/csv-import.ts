import Papa from "papaparse"
import type { components } from "@/api/types/generated"

export type HoldingImportItem = components["schemas"]["HoldingImportItem"]

type HoldingCategory = "Trend_Setter" | "Moat" | "Growth" | "Bond" | "Cash"

export type CsvRow = Record<string, string>

export interface ColumnMapping {
  tickerColumn?: string
  quantityColumn?: string
  categoryColumn?: string
  costBasisColumn?: string
  brokerColumn?: string
  currencyColumn?: string
  accountTypeColumn?: string
  isCashColumn?: string
  categoryDefault?: HoldingCategory
  brokerDefault?: string
  currencyDefault?: string
}

export type ValidationCode =
  | "missing_ticker"
  | "invalid_quantity"
  | "invalid_category"
  | "invalid_currency"

export interface ValidationError {
  code: ValidationCode
  message: string
}

export interface CsvParseWarning {
  row: number
  code: string
  message: string
}

export const CSV_COLUMN_ALIASES: Record<string, string[]> = {
  ticker: ["symbol", "ticker", "stock", "code", "security", "instrument", "name"],
  quantity: ["quantity", "shares", "position", "units", "amount", "qty", "vol"],
  cost_basis: ["cost basis", "avg cost", "average price", "cost", "price", "unit cost", "cost_basis"],
  currency: ["currency", "ccy", "cur"],
  broker: ["broker", "platform", "custodian"],
  category: ["category", "asset class", "asset_class", "type"],
  account_type: ["account type", "account_type", "acct type"],
  is_cash: ["is cash", "is_cash", "cash"],
}

export const CSV_CATEGORY_MAP: Record<string, HoldingCategory> = {
  trend_setter: "Trend_Setter",
  moat: "Moat",
  growth: "Growth",
  bond: "Bond",
  cash: "Cash",
  stock: "Growth",
  equity: "Growth",
  etf: "Growth",
  "fixed income": "Bond",
  "money market": "Cash",
}

const ALLOWED_CATEGORIES = new Set<HoldingCategory>([
  "Trend_Setter",
  "Moat",
  "Growth",
  "Bond",
  "Cash",
])

function normalizeHeader(value: string): string {
  return value.trim().toLowerCase().replace(/[_\s-]+/g, " ")
}

function parseNumber(value: string | undefined): number | null {
  if (!value) return null
  const normalized = value.replace(/,/g, "").trim()
  if (!normalized) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function parseBoolean(value: string | undefined): boolean | null {
  if (!value) return null
  const normalized = value.trim().toLowerCase()
  if (["true", "1", "yes", "y"].includes(normalized)) return true
  if (["false", "0", "no", "n"].includes(normalized)) return false
  return null
}

function mapCategory(raw: string | undefined, fallback: HoldingCategory = "Growth"): HoldingCategory {
  const input = (raw ?? "").trim()
  if (!input) return fallback

  if (ALLOWED_CATEGORIES.has(input as HoldingCategory)) {
    return input as HoldingCategory
  }

  const key = input.toLowerCase().replace(/[_\s-]+/g, " ")
  return CSV_CATEGORY_MAP[key] ?? fallback
}

function pickColumn(headers: string[], aliases: string[]): string | undefined {
  const normalizedHeaders = new Map(headers.map((h) => [normalizeHeader(h), h]))
  for (const alias of aliases) {
    const hit = normalizedHeaders.get(normalizeHeader(alias))
    if (hit) return hit
  }
  return undefined
}

export function autoDetectColumns(headers: string[]): ColumnMapping {
  return {
    tickerColumn: pickColumn(headers, CSV_COLUMN_ALIASES.ticker),
    quantityColumn: pickColumn(headers, CSV_COLUMN_ALIASES.quantity),
    categoryColumn: pickColumn(headers, CSV_COLUMN_ALIASES.category),
    costBasisColumn: pickColumn(headers, CSV_COLUMN_ALIASES.cost_basis),
    brokerColumn: pickColumn(headers, CSV_COLUMN_ALIASES.broker),
    currencyColumn: pickColumn(headers, CSV_COLUMN_ALIASES.currency),
    accountTypeColumn: pickColumn(headers, CSV_COLUMN_ALIASES.account_type),
    isCashColumn: pickColumn(headers, CSV_COLUMN_ALIASES.is_cash),
    categoryDefault: "Growth",
    currencyDefault: "USD",
  }
}

export function transformRow(row: CsvRow, mapping: ColumnMapping): HoldingImportItem {
  const mappedCategory = mapCategory(
    mapping.categoryColumn ? row[mapping.categoryColumn] : undefined,
    mapping.categoryDefault ?? "Growth",
  )
  const currency = (
    mapping.currencyColumn ? row[mapping.currencyColumn] : mapping.currencyDefault ?? "USD"
  )
    .trim()
    .toUpperCase()

  const isCashFromColumn = mapping.isCashColumn ? parseBoolean(row[mapping.isCashColumn]) : null
  const isCash = isCashFromColumn ?? mappedCategory === "Cash"
  const category: HoldingCategory = isCash ? "Cash" : mappedCategory
  const tickerValue = mapping.tickerColumn ? row[mapping.tickerColumn] : ""
  const ticker = (isCash ? currency : tickerValue).trim().toUpperCase()
  const quantity = parseNumber(mapping.quantityColumn ? row[mapping.quantityColumn] : undefined) ?? 0
  const costBasisParsed = parseNumber(
    mapping.costBasisColumn ? row[mapping.costBasisColumn] : undefined,
  )

  return {
    ticker,
    category,
    quantity,
    cost_basis: isCash ? 1.0 : costBasisParsed,
    broker: mapping.brokerColumn ? row[mapping.brokerColumn]?.trim() || null : mapping.brokerDefault || null,
    currency: currency || "USD",
    account_type: mapping.accountTypeColumn ? row[mapping.accountTypeColumn]?.trim() || null : null,
    is_cash: isCash,
  }
}

export function transformRows(rows: CsvRow[], mapping: ColumnMapping): HoldingImportItem[] {
  return rows.map((row) => transformRow(row, mapping))
}

export function validateRow(item: HoldingImportItem): ValidationError[] {
  const errors: ValidationError[] = []

  if (!item.ticker?.trim()) {
    errors.push({ code: "missing_ticker", message: "Ticker is required." })
  }
  if (!Number.isFinite(item.quantity) || item.quantity <= 0) {
    errors.push({ code: "invalid_quantity", message: "Quantity must be greater than 0." })
  }
  if (!ALLOWED_CATEGORIES.has(item.category as HoldingCategory)) {
    errors.push({ code: "invalid_category", message: "Category is invalid." })
  }

  const currency = item.currency?.trim() ?? ""
  if (!/^[A-Z]{3}$/.test(currency)) {
    errors.push({ code: "invalid_currency", message: "Currency must be a 3-letter code." })
  }

  return errors
}

export function validateRows(items: HoldingImportItem[]): Map<number, ValidationError[]> {
  const byRow = new Map<number, ValidationError[]>()
  items.forEach((item, idx) => {
    const errors = validateRow(item)
    if (errors.length > 0) {
      byRow.set(idx, errors)
    }
  })
  return byRow
}

export function isCashRow(item: HoldingImportItem): boolean {
  return item.is_cash || item.category === "Cash"
}

export function parseCsvText(
  input: string,
): Promise<{ headers: string[]; rows: CsvRow[]; warnings: CsvParseWarning[] }> {
  return new Promise((resolve, reject) => {
    Papa.parse<CsvRow>(input, {
      header: true,
      skipEmptyLines: true,
      transformHeader: (header) => header.replace(/^\uFEFF/, "").trim(),
      complete: (result) => {
        const warnings: CsvParseWarning[] = result.errors.map((err) => ({
          row: err.row ?? -1,
          code: err.code,
          message: err.message,
        }))
        const rows = result.data.filter((row) =>
          Object.values(row).some((value) => (value ?? "").toString().trim() !== ""),
        )
        resolve({
          headers: result.meta.fields ?? [],
          rows,
          warnings,
        })
      },
      error: (err: Error) => reject(err),
    })
  })
}

export async function parseCSV(
  file: File,
): Promise<{ headers: string[]; rows: CsvRow[]; warnings: CsvParseWarning[] }> {
  const text = await file.text()
  return parseCsvText(text)
}
