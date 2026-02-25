import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ConsensusStocks } from "../ConsensusStocks"
import type { ConsensusStockItem } from "@/api/types/smartMoney"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key,
  }),
}))

function makeItem(overrides: Partial<ConsensusStockItem> = {}): ConsensusStockItem {
  return {
    ticker: "AAPL",
    company_name: "Apple Inc",
    guru_count: 2,
    gurus: [
      { display_name: "Guru Alpha", action: "NEW_POSITION", weight_pct: 5.0 },
      { display_name: "Guru Beta", action: "INCREASED", weight_pct: 3.0 },
    ],
    total_value: 1_000_000_000,
    avg_weight_pct: 4.0,
    sector: "Technology",
    ...overrides,
  }
}

describe("ConsensusStocks", () => {
  it("shows empty state when items is empty", () => {
    render(<ConsensusStocks items={[]} />)
    expect(
      screen.getByText("smart_money.overview.consensus_empty"),
    ).toBeInTheDocument()
  })

  it("renders ticker and company name", () => {
    render(<ConsensusStocks items={[makeItem()]} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc")).toBeInTheDocument()
  })

  it("renders sector tag when sector is present", () => {
    render(<ConsensusStocks items={[makeItem({ sector: "Technology" })]} />)
    expect(screen.getByText("Technology")).toBeInTheDocument()
  })

  it("does not render sector tag when sector is null", () => {
    render(<ConsensusStocks items={[makeItem({ sector: null })]} />)
    expect(screen.queryByText("Technology")).not.toBeInTheDocument()
  })

  it("renders guru count badge", () => {
    render(<ConsensusStocks items={[makeItem()]} />)
    expect(
      screen.getByText(/2.*smart_money\.overview\.consensus_gurus/),
    ).toBeInTheDocument()
  })

  it("renders avg_weight_pct when present", () => {
    render(<ConsensusStocks items={[makeItem({ avg_weight_pct: 4.0 })]} />)
    expect(screen.getByText(/smart_money\.overview\.avg_weight_label.*4\.0%/)).toBeInTheDocument()
  })

  it("does not render avg weight when avg_weight_pct is null", () => {
    render(<ConsensusStocks items={[makeItem({ avg_weight_pct: null })]} />)
    expect(screen.queryByText(/avg/)).not.toBeInTheDocument()
  })

  it("renders per-guru display names", () => {
    render(<ConsensusStocks items={[makeItem()]} />)
    expect(screen.getByText(/Guru Alpha/)).toBeInTheDocument()
    expect(screen.getByText(/Guru Beta/)).toBeInTheDocument()
  })

  it("renders action badge icons for each guru", () => {
    render(<ConsensusStocks items={[makeItem()]} />)
    // NEW_POSITION → 🟢, INCREASED → 🔵
    expect(screen.getByText(/🟢/)).toBeInTheDocument()
    expect(screen.getByText(/🔵/)).toBeInTheDocument()
  })

  it("renders per-guru weight_pct when present", () => {
    render(<ConsensusStocks items={[makeItem()]} />)
    expect(screen.getByText(/5\.0%/)).toBeInTheDocument()
    expect(screen.getByText(/3\.0%/)).toBeInTheDocument()
  })
})
