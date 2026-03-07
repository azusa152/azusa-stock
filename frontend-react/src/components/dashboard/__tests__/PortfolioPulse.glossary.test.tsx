import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { PortfolioPulse } from "../PortfolioPulse"
import type { FearGreedResponse, RebalanceResponse, TwrResponse } from "@/api/types/dashboard"

const GLOSSARY: Record<string, string> = {
  "glossary.twr": "Time-weighted return definition.",
  "glossary.fear_greed": "Fear and Greed definition.",
  "glossary.market_sentiment": "Market sentiment definition.",
  "glossary.health_score": "Health score definition.",
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (GLOSSARY[key]) return GLOSSARY[key]
      if (params && typeof params === "object") {
        let result = key
        for (const [k, v] of Object.entries(params)) {
          result = result.replace(`{{${k}}}`, String(v))
        }
        return result
      }
      return key
    },
  }),
}))

vi.mock("@/hooks/usePrivacyMode", () => ({
  usePrivacyMode: () => false,
  maskMoney: (v: number) => `$${v.toFixed(2)}`,
}))

vi.mock("@/components/LightweightChartWrapper", () => ({
  LightweightChartWrapper: () => <div data-testid="chart" />,
}))

vi.mock("../InfoPopover", () => ({
  InfoPopover: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const mockRebalance: RebalanceResponse = {
  total_value: 10000,
  total_value_change_pct: 1.5,
  total_value_change: 150,
  display_currency: "USD",
  categories: {},
  advice: [],
  holdings_detail: [],
  xray: [],
  health_score: 100,
  health_level: "healthy",
  sector_exposure: [],
  calculated_at: "2026-03-07T00:00:00Z",
}

const mockFearGreed: FearGreedResponse = {
  composite_score: 60,
  composite_level: "Greed",
  composite_label: "Greed",
  self_calculated_score: null,
  components: [],
  vix: { value: 15.5, change_1d: -0.3, level: "normal", fetched_at: "2026-03-07T00:00:00Z" },
  cnn: { score: 62, label: "Greed", level: "greed", fetched_at: "2026-03-07T00:00:00Z" },
  fetched_at: "2026-03-07T00:00:00Z",
}

const mockTwr: TwrResponse = {
  twr_pct: 5.2,
  start_date: "2026-01-01",
  end_date: "2026-03-07",
  snapshot_count: 65,
}

const BASE_PROPS: Parameters<typeof PortfolioPulse>[0] = {
  rebalance: mockRebalance,
  fearGreed: mockFearGreed,
  twr: mockTwr,
  snapshots: [],
  lastScan: { market_status: "positive", market_status_details: "Bull run" },
  stocks: [],
  enrichedStocks: [],
  holdings: [{ id: 1 }],
  isLoading: false,
}

describe("PortfolioPulse – glossary integration", () => {
  it("wraps YTD Return with a glossary tooltip trigger", () => {
    render(<PortfolioPulse {...BASE_PROPS} />)
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.twr"] })
    expect(trigger).toBeInTheDocument()
    expect(trigger).toHaveTextContent("dashboard.ytd_return")
  })

  it("wraps Fear & Greed title with a glossary tooltip trigger", () => {
    render(<PortfolioPulse {...BASE_PROPS} />)
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.fear_greed"] })
    expect(trigger).toBeInTheDocument()
  })

  it("wraps Market Sentiment with a glossary tooltip trigger", () => {
    render(<PortfolioPulse {...BASE_PROPS} />)
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.market_sentiment"] })
    expect(trigger).toBeInTheDocument()
  })

  it("wraps Health Score with a glossary tooltip trigger", () => {
    render(<PortfolioPulse {...BASE_PROPS} />)
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.health_score"] })
    expect(trigger).toBeInTheDocument()
  })

  it("renders loading skeleton when isLoading is true", () => {
    render(<PortfolioPulse {...BASE_PROPS} isLoading={true} />)
    expect(screen.queryByRole("button", { name: GLOSSARY["glossary.twr"] })).not.toBeInTheDocument()
  })
})
