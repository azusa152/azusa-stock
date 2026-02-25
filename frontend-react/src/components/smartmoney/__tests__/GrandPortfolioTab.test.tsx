import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { GrandPortfolioTab } from "../GrandPortfolioTab"
import type { GrandPortfolioResponse } from "@/api/types/smartMoney"

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

vi.mock("../SectorChart", () => ({
  SectorChart: ({ data }: { data: unknown[] }) => (
    <div data-testid="sector-chart">{data.length} sectors</div>
  ),
}))

vi.mock("../ActionBadge", () => ({
  ActionBadge: ({ action }: { action: string }) => <span>{action}</span>,
}))

const mockUseGrandPortfolio = vi.fn()
vi.mock("@/api/hooks/useSmartMoney", () => ({
  useGrandPortfolio: () => mockUseGrandPortfolio(),
}))

function makeGrandPortfolioResponse(
  overrides: Partial<GrandPortfolioResponse> = {},
): GrandPortfolioResponse {
  return {
    items: [],
    total_value: 0,
    unique_tickers: 0,
    sector_breakdown: [],
    ...overrides,
  }
}

describe("GrandPortfolioTab", () => {
  it("renders loading skeleton when isLoading", () => {
    mockUseGrandPortfolio.mockReturnValue({ data: undefined, isLoading: true })
    const { container } = render(<GrandPortfolioTab />)
    // Skeleton renders a div, not the table or cards
    expect(container.querySelector("table")).toBeNull()
  })

  it("renders empty state when items is empty", () => {
    mockUseGrandPortfolio.mockReturnValue({
      data: makeGrandPortfolioResponse(),
      isLoading: false,
    })
    render(<GrandPortfolioTab />)
    expect(screen.getByText("smart_money.grand_portfolio.no_data")).toBeInTheDocument()
  })

  it("renders summary cards with total_value and unique_tickers", () => {
    mockUseGrandPortfolio.mockReturnValue({
      data: makeGrandPortfolioResponse({
        items: [
          {
            ticker: "AAPL",
            company_name: "Apple Inc",
            sector: "Technology",
            guru_count: 2,
            gurus: ["Buffett"],
            total_value: 500_000_000_000,
            avg_weight_pct: 5.5,
            combined_weight_pct: 10.0,
            dominant_action: "UNCHANGED",
          },
        ],
        total_value: 2_400_000_000_000,
        unique_tickers: 42,
        sector_breakdown: [{ sector: "Technology", total_value: 1_000_000, holding_count: 1, weight_pct: 100 }],
      }),
      isLoading: false,
    })
    render(<GrandPortfolioTab />)
    expect(screen.getByText("smart_money.grand_portfolio.total_aum")).toBeInTheDocument()
    expect(screen.getByText("smart_money.grand_portfolio.unique_tickers")).toBeInTheDocument()
    expect(screen.getByText("42")).toBeInTheDocument()
  })

  it("renders holdings table with ticker and action badge", () => {
    mockUseGrandPortfolio.mockReturnValue({
      data: makeGrandPortfolioResponse({
        items: [
          {
            ticker: "MSFT",
            company_name: "Microsoft Corp",
            sector: "Technology",
            guru_count: 3,
            gurus: ["Buffett", "Dalio", "Tepper"],
            total_value: 300_000_000,
            avg_weight_pct: 4.0,
            combined_weight_pct: 8.5,
            dominant_action: "INCREASED",
          },
        ],
        total_value: 3_000_000_000,
        unique_tickers: 1,
        sector_breakdown: [],
      }),
      isLoading: false,
    })
    render(<GrandPortfolioTab />)
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("Microsoft Corp")).toBeInTheDocument()
    expect(screen.getByText("8.50%")).toBeInTheDocument()
    expect(screen.getByText("INCREASED")).toBeInTheDocument()
  })

  it("renders sector chart", () => {
    mockUseGrandPortfolio.mockReturnValue({
      data: makeGrandPortfolioResponse({
        items: [
          {
            ticker: "NVDA",
            company_name: "Nvidia",
            sector: "Technology",
            guru_count: 1,
            gurus: ["Dalio"],
            total_value: 100_000_000,
            avg_weight_pct: 3.0,
            combined_weight_pct: 5.0,
            dominant_action: "NEW_POSITION",
          },
        ],
        total_value: 100_000_000,
        unique_tickers: 1,
        sector_breakdown: [
          { sector: "Technology", total_value: 100_000_000, holding_count: 1, weight_pct: 100 },
        ],
      }),
      isLoading: false,
    })
    render(<GrandPortfolioTab />)
    expect(screen.getByTestId("sector-chart")).toBeInTheDocument()
  })

  it("renders two ticker rows in the table", () => {
    mockUseGrandPortfolio.mockReturnValue({
      data: makeGrandPortfolioResponse({
        items: [
          {
            ticker: "AAPL",
            company_name: "Apple",
            sector: null,
            guru_count: 1,
            gurus: ["Buffett"],
            total_value: 600_000,
            avg_weight_pct: null,
            combined_weight_pct: 60.0,
            dominant_action: "UNCHANGED",
          },
          {
            ticker: "TSLA",
            company_name: "Tesla",
            sector: null,
            guru_count: 1,
            gurus: ["Cathie"],
            total_value: 400_000,
            avg_weight_pct: null,
            combined_weight_pct: 40.0,
            dominant_action: "INCREASED",
          },
        ],
        total_value: 1_000_000,
        unique_tickers: 2,
        sector_breakdown: [],
      }),
      isLoading: false,
    })
    const { container } = render(<GrandPortfolioTab />)
    const bodyRows = container.querySelectorAll("tbody tr")
    expect(bodyRows).toHaveLength(2)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
  })
})
