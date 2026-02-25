import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { GuruTab } from "../GuruTab"
import type { GuruHolding } from "@/api/types/smartMoney"

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key,
  }),
}))

vi.mock("@/hooks/useRechartsTheme", () => ({
  useRechartsTheme: () => ({
    tickColor: "#666",
    gridColor: "#eee",
    tooltipBg: "#fff",
    tooltipBorder: "#ccc",
    tooltipText: "#000",
    tooltipStyle: {},
  }),
}))

vi.mock("../ActionBadge", () => ({
  ActionBadge: ({ action }: { action: string }) => <span>{action}</span>,
}))

vi.mock("../QoQTable", () => ({
  QoQTable: () => <div data-testid="qoq-table" />,
}))

// Mock all useSmartMoney hooks at the module level
const mockUseGuruFiling = vi.fn()
const mockUseGuruFilings = vi.fn()
const mockUseGuruHoldingChanges = vi.fn()
const mockUseGuruTopHoldings = vi.fn()
const mockUseGreatMinds = vi.fn()
const mockUseGuruQoQ = vi.fn()
const mockUseSyncGuru = vi.fn()

vi.mock("@/api/hooks/useSmartMoney", () => ({
  useGuruFiling: () => mockUseGuruFiling(),
  useGuruFilings: () => mockUseGuruFilings(),
  useGuruHoldingChanges: () => mockUseGuruHoldingChanges(),
  useGuruTopHoldings: () => mockUseGuruTopHoldings(),
  useGreatMinds: () => mockUseGreatMinds(),
  useGuruQoQ: () => mockUseGuruQoQ(),
  useSyncGuru: () => mockUseSyncGuru(),
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeHolding(overrides: Partial<GuruHolding> = {}): GuruHolding {
  return {
    guru_id: 1,
    cusip: "TEST0001",
    ticker: "TEST",
    company_name: "Test Corp",
    value: 1_000_000,
    shares: 10000,
    action: "NEW_POSITION",
    change_pct: null,
    weight_pct: 10.0,
    report_date: "2024-12-31",
    filing_date: "2025-02-14",
    price_change_pct: null,
    ...overrides,
  }
}

function setupDefaultMocks() {
  mockUseGuruFiling.mockReturnValue({ data: undefined, isLoading: false })
  mockUseGuruFilings.mockReturnValue({ data: undefined })
  mockUseGuruQoQ.mockReturnValue({ data: undefined })
  mockUseGreatMinds.mockReturnValue({ data: undefined })
  mockUseSyncGuru.mockReturnValue({ isPending: false, isSuccess: false, isError: false, mutate: vi.fn() })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("GuruTab — performance column in Holding Changes table", () => {
  it("renders +12.5% with green styling when price_change_pct is positive", () => {
    setupDefaultMocks()
    mockUseGuruHoldingChanges.mockReturnValue({
      data: [makeHolding({ price_change_pct: 12.5 })],
      isLoading: false,
    })
    mockUseGuruTopHoldings.mockReturnValue({ data: [], isLoading: false })

    render(<GuruTab guruId={1} guruName="Buffett" enabled={true} />)

    const perfCell = screen.getByText("+12.5%")
    expect(perfCell).toBeInTheDocument()
    expect(perfCell.className).toMatch(/green/)
  })

  it("renders -5.0% with red styling when price_change_pct is negative", () => {
    setupDefaultMocks()
    mockUseGuruHoldingChanges.mockReturnValue({
      data: [makeHolding({ price_change_pct: -5.0 })],
      isLoading: false,
    })
    mockUseGuruTopHoldings.mockReturnValue({ data: [], isLoading: false })

    render(<GuruTab guruId={1} guruName="Buffett" enabled={true} />)

    const perfCell = screen.getByText("-5.0%")
    expect(perfCell).toBeInTheDocument()
    expect(perfCell.className).toMatch(/red/)
  })

  it("renders — when price_change_pct is null", () => {
    setupDefaultMocks()
    mockUseGuruHoldingChanges.mockReturnValue({
      data: [makeHolding({ price_change_pct: null })],
      isLoading: false,
    })
    mockUseGuruTopHoldings.mockReturnValue({ data: [], isLoading: false })

    render(<GuruTab guruId={1} guruName="Buffett" enabled={true} />)

    // The — spans for null performance values; find one inside the changes table
    const dashSpans = screen.getAllByText("—")
    expect(dashSpans.length).toBeGreaterThan(0)
  })
})

describe("GuruTab — performance column in Top Holdings table", () => {
  it("renders +20.0% in green for top holding with positive performance", () => {
    setupDefaultMocks()
    mockUseGuruHoldingChanges.mockReturnValue({ data: [], isLoading: false })
    mockUseGuruTopHoldings.mockReturnValue({
      data: [makeHolding({ action: "UNCHANGED", price_change_pct: 20.0 })],
      isLoading: false,
    })

    render(<GuruTab guruId={1} guruName="Buffett" enabled={true} />)

    const perfCell = screen.getByText("+20.0%")
    expect(perfCell).toBeInTheDocument()
    expect(perfCell.className).toMatch(/green/)
  })

  it("renders — for top holding with null performance", () => {
    setupDefaultMocks()
    mockUseGuruHoldingChanges.mockReturnValue({ data: [], isLoading: false })
    mockUseGuruTopHoldings.mockReturnValue({
      data: [makeHolding({ action: "UNCHANGED", price_change_pct: null })],
      isLoading: false,
    })

    render(<GuruTab guruId={1} guruName="Buffett" enabled={true} />)

    const dashSpans = screen.getAllByText("—")
    expect(dashSpans.length).toBeGreaterThan(0)
  })
})
