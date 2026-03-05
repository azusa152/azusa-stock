import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { NetWorthSummary } from "../NetWorthSummary"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/components/LightweightChartWrapper", () => ({
  LightweightChartWrapper: () => <div data-testid="sparkline" />,
}))

describe("NetWorthSummary", () => {
  beforeEach(() => {
    usePrivacyMode.setState({ isPrivate: false })
  })

  it("renders empty state when there are no items", () => {
    render(
      <MemoryRouter>
        <NetWorthSummary
          summary={{
            display_currency: "USD",
            investment_value: 0,
            other_assets_value: 0,
            liabilities_value: 0,
            net_worth: 0,
            breakdown: {},
            stale_count: 0,
            items: [],
            calculated_at: "2026-03-05T00:00:00Z",
          }}
          history={[]}
          isLoading={false}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText("net_worth.empty")).toBeInTheDocument()
  })

  it("renders net worth and manage link when data exists", () => {
    render(
      <MemoryRouter>
        <NetWorthSummary
          summary={{
            display_currency: "USD",
            investment_value: 1000,
            other_assets_value: 200,
            liabilities_value: 100,
            net_worth: 1100,
            breakdown: {},
            stale_count: 0,
            items: [
              {
                id: 1,
                name: "Savings",
                kind: "asset",
                category: "savings",
                value: 200,
                value_display: 200,
                currency: "USD",
                interest_rate: null,
                note: "",
                is_active: true,
                is_stale: false,
                days_since_update: 0,
                created_at: "2026-03-05T00:00:00Z",
                updated_at: "2026-03-05T00:00:00Z",
              },
            ],
            calculated_at: "2026-03-05T00:00:00Z",
          }}
          history={[
            {
              snapshot_date: "2026-03-01",
              investment_value: 1000,
              other_assets_value: 100,
              liabilities_value: 100,
              net_worth: 1000,
              display_currency: "USD",
              breakdown: {},
            },
            {
              snapshot_date: "2026-03-05",
              investment_value: 1000,
              other_assets_value: 200,
              liabilities_value: 100,
              net_worth: 1100,
              display_currency: "USD",
              breakdown: {},
            },
          ]}
          isLoading={false}
        />
      </MemoryRouter>,
    )

    expect(screen.getAllByText("$1,100.00").length).toBeGreaterThan(0)
    expect(screen.getByRole("link", { name: "dashboard.net_worth_manage" })).toBeInTheDocument()
  })
})
