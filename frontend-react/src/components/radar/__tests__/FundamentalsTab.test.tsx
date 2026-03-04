import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { FundamentalsTab } from "../FundamentalsTab"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useFundamentals: () => ({ data: undefined, isLoading: false }),
}))

describe("FundamentalsTab", () => {
  it("renders no-data state when fundamentals missing", () => {
    render(<FundamentalsTab ticker="NVDA" fundamentals={undefined} />)
    expect(
      screen.getByText("radar.stock_card.fundamentals.no_data"),
    ).toBeInTheDocument()
  })

  it("renders key metrics when fundamentals exist", () => {
    render(
      <FundamentalsTab
        ticker="NVDA"
        fundamentals={{
          trailing_pe: 18.2,
          market_cap: 1_000_000_000,
          return_on_equity: 0.2,
          revenue_growth: 0.12,
          earnings_growth: 0.15,
        }}
      />,
    )
    expect(
      screen.getByText("radar.stock_card.fundamentals.trailing_pe"),
    ).toBeInTheDocument()
    expect(screen.getByText("18.20")).toBeInTheDocument()
    expect(screen.getByText("1B")).toBeInTheDocument()
  })
})
