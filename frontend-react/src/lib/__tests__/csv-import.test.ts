import { describe, expect, it } from "vitest"
import {
  autoDetectColumns,
  parseCsvText,
  transformRows,
  validateRows,
  type ColumnMapping,
} from "@/lib/csv-import"

describe("csv-import", () => {
  it("auto-detects common column aliases", () => {
    const mapping = autoDetectColumns([
      "Symbol",
      "Shares",
      "Avg Cost",
      "Currency",
      "Broker",
      "Account Type",
      "Category",
    ])

    expect(mapping.tickerColumn).toBe("Symbol")
    expect(mapping.quantityColumn).toBe("Shares")
    expect(mapping.costBasisColumn).toBe("Avg Cost")
    expect(mapping.currencyColumn).toBe("Currency")
    expect(mapping.brokerColumn).toBe("Broker")
    expect(mapping.accountTypeColumn).toBe("Account Type")
    expect(mapping.categoryColumn).toBe("Category")
  })

  it("parses BOM-prefixed CSV text", async () => {
    const parsed = await parseCsvText("\uFEFFticker,quantity,category,currency\nAAPL,10,Growth,USD\n")
    expect(parsed.headers).toEqual(["ticker", "quantity", "category", "currency"])
    expect(parsed.rows).toHaveLength(1)
    expect(parsed.warnings).toHaveLength(0)
  })

  it("parses TSV text", async () => {
    const parsed = await parseCsvText("ticker\tquantity\tcategory\tcurrency\nMSFT\t5\tMoat\tUSD\n")
    expect(parsed.rows).toHaveLength(1)
    expect(parsed.rows[0]?.ticker).toBe("MSFT")
    expect(parsed.warnings).toHaveLength(0)
  })

  it("returns header with zero rows for header-only input", async () => {
    const parsed = await parseCsvText("ticker,quantity,category,currency\n")
    expect(parsed.headers).toEqual(["ticker", "quantity", "category", "currency"])
    expect(parsed.rows).toHaveLength(0)
    expect(parsed.warnings).toHaveLength(0)
  })

  it("returns empty headers and rows for empty input", async () => {
    const parsed = await parseCsvText("")
    expect(parsed.headers).toEqual([])
    expect(parsed.rows).toHaveLength(0)
  })

  it("keeps valid rows and returns parser warnings", async () => {
    const parsed = await parseCsvText(
      'ticker,quantity,category,currency\n"AAPL",10,Growth,USD\n"MSFT,5,Moat,USD\n',
    )
    expect(parsed.rows.some((row) => row.ticker === "AAPL")).toBe(true)
    expect(parsed.warnings.length).toBeGreaterThan(0)
  })

  it("transforms rows and handles cash rows", () => {
    const mapping: ColumnMapping = {
      tickerColumn: "symbol",
      quantityColumn: "qty",
      categoryColumn: "type",
      currencyColumn: "ccy",
      costBasisColumn: "cost",
      brokerColumn: "broker",
      accountTypeColumn: "account",
      categoryDefault: "Growth",
      currencyDefault: "USD",
    }

    const items = transformRows(
      [
        {
          symbol: "AAPL",
          qty: "10",
          type: "Growth",
          ccy: "usd",
          cost: "150.25",
          broker: "IBKR",
          account: "",
        },
        {
          symbol: "",
          qty: "50000",
          type: "Cash",
          ccy: "twd",
          cost: "",
          broker: "Bank",
          account: "savings",
        },
      ],
      mapping,
    )

    expect(items[0]).toMatchObject({
      ticker: "AAPL",
      quantity: 10,
      category: "Growth",
      currency: "USD",
      cost_basis: 150.25,
      is_cash: false,
    })

    expect(items[1]).toMatchObject({
      ticker: "TWD",
      quantity: 50000,
      category: "Cash",
      currency: "TWD",
      cost_basis: 1.0,
      account_type: "savings",
      is_cash: true,
    })
  })

  it("treats row as cash when is_cash column is true", () => {
    const mapping: ColumnMapping = {
      tickerColumn: "symbol",
      quantityColumn: "qty",
      categoryColumn: "type",
      currencyColumn: "ccy",
      isCashColumn: "is_cash",
      categoryDefault: "Growth",
      currencyDefault: "USD",
    }

    const items = transformRows(
      [
        {
          symbol: "SHOULD_BE_IGNORED",
          qty: "2500",
          type: "Growth",
          ccy: "usd",
          is_cash: "true",
        },
      ],
      mapping,
    )

    expect(items[0]).toMatchObject({
      ticker: "USD",
      quantity: 2500,
      category: "Cash",
      currency: "USD",
      cost_basis: 1.0,
      is_cash: true,
    })
  })

  it("validates invalid rows", () => {
    const errors = validateRows([
      {
        ticker: "",
        category: "Growth",
        quantity: 0,
        currency: "US",
        cost_basis: null,
        broker: null,
        account_type: null,
        is_cash: false,
      },
    ])

    expect(errors.size).toBe(1)
    const rowErrors = errors.get(0) ?? []
    expect(rowErrors.some((e) => e.code === "missing_ticker")).toBe(true)
    expect(rowErrors.some((e) => e.code === "invalid_quantity")).toBe(true)
    expect(rowErrors.some((e) => e.code === "invalid_currency")).toBe(true)
  })

  it("normalizes mixed-case values and keeps CJK broker/account text", () => {
    const mapping: ColumnMapping = {
      tickerColumn: " ticker ",
      quantityColumn: "quantity",
      categoryColumn: "category",
      currencyColumn: "currency",
      brokerColumn: "broker",
      accountTypeColumn: "account_type",
      categoryDefault: "Growth",
      currencyDefault: "USD",
    }

    const items = transformRows(
      [
        {
          " ticker ": " 2330.tw ",
          quantity: "-5",
          category: "gRoWtH",
          currency: "twd",
          broker: "玉山證券",
          account_type: "一般帳戶",
        },
      ],
      mapping,
    )

    expect(items[0]).toMatchObject({
      ticker: "2330.TW",
      category: "Growth",
      currency: "TWD",
      broker: "玉山證券",
      account_type: "一般帳戶",
    })

    const rowErrors = validateRows(items).get(0) ?? []
    expect(rowErrors.some((e) => e.code === "invalid_quantity")).toBe(true)
  })

  it("handles 1000+ rows without throwing", () => {
    const mapping: ColumnMapping = {
      tickerColumn: "ticker",
      quantityColumn: "quantity",
      categoryColumn: "category",
      currencyColumn: "currency",
      categoryDefault: "Growth",
      currencyDefault: "USD",
    }
    const rows = Array.from({ length: 1001 }, (_, idx) => ({
      ticker: `TEST${idx}`,
      quantity: "1",
      category: "Growth",
      currency: "USD",
    }))

    const items = transformRows(rows, mapping)
    expect(items).toHaveLength(1001)
  })
})
