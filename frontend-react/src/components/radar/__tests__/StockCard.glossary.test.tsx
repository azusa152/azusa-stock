import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { StockCard } from "../StockCard"
import type { RadarStock, RadarEnrichedStock } from "@/api/types/radar"

const GLOSSARY: Record<string, string> = {
  "glossary.rsi": "RSI definition.",
  "glossary.bias": "Bias definition.",
  "glossary.volume_ratio": "Volume ratio definition.",
  "glossary.ma200": "MA200 definition.",
  "glossary.ma60": "MA60 definition.",
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (GLOSSARY[key]) return GLOSSARY[key]
      if (params && "defaultValue" in params) return params.defaultValue as string
      return key
    },
  }),
}))

vi.mock("@/components/LightweightChartWrapper", () => ({
  LightweightChartWrapper: () => <div data-testid="chart" />,
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useAddThesis: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateCategory: () => ({ mutate: vi.fn(), isPending: false }),
  useDeactivateStock: () => ({ mutate: vi.fn(), isPending: false }),
  useThesisHistory: () => ({ data: [], isLoading: false }),
  usePriceHistory: () => ({ data: [], isLoading: false }),
  useMoatAnalysis: () => ({ data: null, isLoading: false }),
}))

vi.mock("@/components/radar/PriceChart", () => ({
  PriceChart: () => <div data-testid="price-chart" />,
}))

vi.mock("@/components/radar/GrossMarginChart", () => ({
  GrossMarginChart: () => <div data-testid="gm-chart" />,
}))

vi.mock("@/components/radar/SparklineHeader", () => ({
  SparklineHeader: () => <div data-testid="sparkline-header" />,
}))

vi.mock("@/components/radar/FundamentalsTab", () => ({
  FundamentalsTab: () => <div data-testid="fundamentals" />,
}))

const STOCK: RadarStock = {
  ticker: "AAPL",
  category: "Growth",
  current_thesis: "Strong ecosystem moat",
  current_tags: ["tech"],
  display_order: 0,
  last_scan_signal: "NORMAL",
  signal_since: null,
  is_active: true,
  is_etf: false,
} as RadarStock

const ENRICHMENT: RadarEnrichedStock = {
  ticker: "AAPL",
  price: 185.5,
  change_pct: 1.2,
  computed_signal: "NORMAL",
  last_scan_signal: "NORMAL",
  rsi: 55.3,
  bias: 3.2,
  volume_ratio: 1.4,
  market_cap: 2_800_000_000_000,
  signals: {
    price: 185.5,
    previous_close: 183.3,
    change_pct: 1.2,
    rsi: 55.3,
    bias: 3.2,
    volume_ratio: 1.4,
    ma200: 170.0,
    ma60: 178.0,
  },
  fundamentals: { market_cap: 2_800_000_000_000 },
} as unknown as RadarEnrichedStock

describe("StockCard – glossary integration", () => {
  async function renderExpanded() {
    const user = userEvent.setup()
    render(<StockCard stock={STOCK} enrichment={ENRICHMENT} index={0} />)
    const expandBtn = screen.getByRole("button", { name: /AAPL/i })
    await user.click(expandBtn)
  }

  it("renders RSI glossary trigger when expanded", async () => {
    await renderExpanded()
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.rsi"] })
    expect(trigger).toBeInTheDocument()
    expect(trigger).toHaveTextContent("utils.signals.rsi")
  })

  it("renders Bias glossary trigger when expanded", async () => {
    await renderExpanded()
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.bias"] })
    expect(trigger).toBeInTheDocument()
  })

  it("renders Volume Ratio glossary trigger when expanded", async () => {
    await renderExpanded()
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.volume_ratio"] })
    expect(trigger).toBeInTheDocument()
  })

  it("renders MA200 glossary trigger in metrics tab", async () => {
    await renderExpanded()
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.ma200"] })
    expect(trigger).toBeInTheDocument()
  })

  it("renders MA60 glossary trigger in metrics tab", async () => {
    await renderExpanded()
    const trigger = screen.getByRole("button", { name: GLOSSARY["glossary.ma60"] })
    expect(trigger).toBeInTheDocument()
  })

  it("does not render glossary triggers when collapsed", () => {
    render(<StockCard stock={STOCK} enrichment={ENRICHMENT} index={0} />)
    expect(screen.queryByRole("button", { name: GLOSSARY["glossary.rsi"] })).not.toBeInTheDocument()
  })
})
