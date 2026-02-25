import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { QoQTable } from "../QoQTable"
import type { QoQResponse } from "@/api/types/smartMoney"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key,
  }),
}))

function makeQoQResponse(overrides: Partial<QoQResponse> = {}): QoQResponse {
  return {
    guru_id: 1,
    items: [],
    ...overrides,
  }
}

describe("QoQTable", () => {
  it("renders empty state when items is empty", () => {
    render(<QoQTable data={makeQoQResponse()} />)
    expect(screen.getByText("smart_money.qoq.no_data")).toBeInTheDocument()
  })

  it("renders quarter headers from first item's quarters", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: "AAPL",
          company_name: "Apple Inc",
          trend: "increasing",
          quarters: [
            { report_date: "2024-12-31", shares: 1200, value: 300000, weight_pct: 60.0, action: "INCREASED" },
            { report_date: "2024-09-30", shares: 1000, value: 250000, weight_pct: 55.0, action: "UNCHANGED" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("2024-12-31")).toBeInTheDocument()
    expect(screen.getByText("2024-09-30")).toBeInTheDocument()
  })

  it("renders ticker and company name", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: "MSFT",
          company_name: "Microsoft Corp",
          trend: "stable",
          quarters: [
            { report_date: "2024-12-31", shares: 500, value: 200000, weight_pct: 40.0, action: "UNCHANGED" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("Microsoft Corp")).toBeInTheDocument()
  })

  it("renders trend indicator for increasing", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: "NVDA",
          company_name: "Nvidia Corp",
          trend: "increasing",
          quarters: [
            { report_date: "2024-12-31", shares: 2000, value: 500000, weight_pct: 70.0, action: "INCREASED" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("↑")).toBeInTheDocument()
  })

  it("renders trend indicator for decreasing", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: "TSLA",
          company_name: "Tesla Inc",
          trend: "decreasing",
          quarters: [
            { report_date: "2024-12-31", shares: 500, value: 100000, weight_pct: 20.0, action: "DECREASED" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("↓")).toBeInTheDocument()
  })

  it("renders weight_pct when present", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: "AAPL",
          company_name: "Apple Inc",
          trend: "stable",
          quarters: [
            { report_date: "2024-12-31", shares: 1000, value: 200000, weight_pct: 45.5, action: "UNCHANGED" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("45.5%")).toBeInTheDocument()
  })

  it("renders dash when ticker is null", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: null,
          company_name: "Unknown Corp",
          trend: "stable",
          quarters: [
            { report_date: "2024-12-31", shares: 100, value: 10000, weight_pct: null, action: "UNCHANGED" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("—")).toBeInTheDocument()
  })

  it("renders trend column header", () => {
    const data = makeQoQResponse({
      items: [
        {
          ticker: "GOOG",
          company_name: "Alphabet",
          trend: "new",
          quarters: [
            { report_date: "2024-12-31", shares: 300, value: 80000, weight_pct: 15.0, action: "NEW_POSITION" },
          ],
        },
      ],
    })
    render(<QoQTable data={data} />)
    expect(screen.getByText("smart_money.qoq.trend")).toBeInTheDocument()
  })

  it("aligns columns correctly when items have fewer quarters than the header", () => {
    // AAPL has 3 quarters (defines headers), NVDA only has 2 (missing 2024-03-31)
    const data = makeQoQResponse({
      items: [
        {
          ticker: "AAPL",
          company_name: "Apple Inc",
          trend: "increasing",
          quarters: [
            { report_date: "2024-09-30", shares: 1200, value: 300000, weight_pct: 50.0, action: "UNCHANGED" },
            { report_date: "2024-06-30", shares: 1100, value: 280000, weight_pct: 48.0, action: "UNCHANGED" },
            { report_date: "2024-03-31", shares: 1000, value: 260000, weight_pct: 45.0, action: "UNCHANGED" },
          ],
        },
        {
          ticker: "NVDA",
          company_name: "Nvidia Corp",
          trend: "new",
          quarters: [
            { report_date: "2024-09-30", shares: 600, value: 200000, weight_pct: 40.0, action: "INCREASED" },
            { report_date: "2024-06-30", shares: 500, value: 180000, weight_pct: 38.0, action: "NEW_POSITION" },
          ],
        },
      ],
    })
    const { container } = render(<QoQTable data={data} />)

    // Header row: ticker + company + 3 quarter cols + trend = 6 th
    const headerCells = container.querySelectorAll("thead th")
    expect(headerCells).toHaveLength(6)

    // Each body row must also have 6 td to match the header
    const bodyRows = container.querySelectorAll("tbody tr")
    expect(bodyRows).toHaveLength(2)
    bodyRows.forEach((row) => {
      expect(row.querySelectorAll("td")).toHaveLength(6)
    })
  })
})
