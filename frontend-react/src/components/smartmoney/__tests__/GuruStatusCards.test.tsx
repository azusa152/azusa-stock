import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { GuruStatusCards } from "../GuruStatusCards"
import type { GuruSummaryItem } from "@/api/types/smartMoney"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key,
  }),
}))

vi.mock("@/api/hooks/useSmartMoney", () => ({
  useSyncGuru: () => ({ isPending: false, variables: undefined, mutate: vi.fn() }),
}))

function makeGuru(overrides: Partial<GuruSummaryItem> = {}): GuruSummaryItem {
  return {
    id: 1,
    display_name: "Warren Buffett",
    latest_report_date: "2025-01-01",
    latest_filing_date: "2025-02-14",
    total_value: 500_000_000_000,
    holdings_count: 40,
    filing_count: 8,
    style: null,
    tier: null,
    top5_concentration_pct: null,
    turnover_pct: null,
    ...overrides,
  }
}

describe("GuruStatusCards", () => {
  it("renders a card for each guru", () => {
    const gurus = [
      makeGuru({ id: 1, display_name: "Warren Buffett" }),
      makeGuru({ id: 2, display_name: "Ray Dalio" }),
    ]
    render(<GuruStatusCards gurus={gurus} />)
    expect(screen.getByText("Warren Buffett")).toBeInTheDocument()
    expect(screen.getByText("Ray Dalio")).toBeInTheDocument()
  })

  it("shows empty state when gurus array is empty", () => {
    render(<GuruStatusCards gurus={[]} />)
    expect(screen.getByText("smart_money.overview.no_data")).toBeInTheDocument()
  })

  it("renders style badge when style is set", () => {
    render(<GuruStatusCards gurus={[makeGuru({ style: "VALUE" })]} />)
    expect(screen.getByText("VALUE")).toBeInTheDocument()
  })

  it("does not render a style badge when style is null", () => {
    render(<GuruStatusCards gurus={[makeGuru({ style: null })]} />)
    // No badge span — display_name is still present
    expect(screen.getByText("Warren Buffett")).toBeInTheDocument()
    expect(screen.queryByText("VALUE")).not.toBeInTheDocument()
  })

  it("renders 3 stars for TIER_1", () => {
    render(<GuruStatusCards gurus={[makeGuru({ tier: "TIER_1" })]} />)
    expect(screen.getByText("★★★")).toBeInTheDocument()
  })

  it("renders 2 stars for TIER_2", () => {
    render(<GuruStatusCards gurus={[makeGuru({ tier: "TIER_2" })]} />)
    expect(screen.getByText("★★")).toBeInTheDocument()
  })

  it("renders 1 star for TIER_3", () => {
    render(<GuruStatusCards gurus={[makeGuru({ tier: "TIER_3" })]} />)
    expect(screen.getByText("★")).toBeInTheDocument()
  })

  it("renders no stars when tier is null", () => {
    render(<GuruStatusCards gurus={[makeGuru({ tier: null })]} />)
    expect(screen.queryByText("★")).not.toBeInTheDocument()
  })

  it("renders both style badge and tier stars together", () => {
    render(<GuruStatusCards gurus={[makeGuru({ style: "MACRO", tier: "TIER_1" })]} />)
    expect(screen.getByText("MACRO")).toBeInTheDocument()
    expect(screen.getByText("★★★")).toBeInTheDocument()
  })

  it("renders top5_concentration_pct when present", () => {
    render(<GuruStatusCards gurus={[makeGuru({ top5_concentration_pct: 45.5 })]} />)
    expect(screen.getByText(/45\.5%/)).toBeInTheDocument()
    expect(screen.getByText("smart_money.metric.concentration")).toBeInTheDocument()
  })

  it("renders 'high conviction' label when top5_concentration_pct >= 60", () => {
    render(<GuruStatusCards gurus={[makeGuru({ top5_concentration_pct: 72.0 })]} />)
    expect(screen.getByText("smart_money.metric.high_conviction")).toBeInTheDocument()
  })

  it("renders 'diversified' label when top5_concentration_pct <= 30", () => {
    render(<GuruStatusCards gurus={[makeGuru({ top5_concentration_pct: 25.0 })]} />)
    expect(screen.getByText("smart_money.metric.diversified")).toBeInTheDocument()
  })

  it("does not render conviction label for mid-range concentration", () => {
    render(<GuruStatusCards gurus={[makeGuru({ top5_concentration_pct: 45.0 })]} />)
    expect(screen.queryByText("smart_money.metric.high_conviction")).not.toBeInTheDocument()
    expect(screen.queryByText("smart_money.metric.diversified")).not.toBeInTheDocument()
  })

  it("renders turnover_pct when present", () => {
    render(<GuruStatusCards gurus={[makeGuru({ turnover_pct: 33.0 })]} />)
    expect(screen.getByText(/33%/)).toBeInTheDocument()
    expect(screen.getByText("smart_money.metric.turnover")).toBeInTheDocument()
  })

  it("does not render concentration or turnover when both are null", () => {
    render(<GuruStatusCards gurus={[makeGuru({ top5_concentration_pct: null, turnover_pct: null })]} />)
    expect(screen.queryByText("smart_money.metric.concentration")).not.toBeInTheDocument()
    expect(screen.queryByText("smart_money.metric.turnover")).not.toBeInTheDocument()
  })
})
