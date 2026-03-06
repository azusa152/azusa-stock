import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { CategoryTabs } from "../CategoryTabs"
import type { RadarStock } from "@/api/types/radar"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: { count?: number }) =>
      typeof params?.count === "number" ? `${key} (${params.count})` : key,
  }),
}))

vi.mock("../StockCard", () => ({
  StockCard: () => <div>stock-card</div>,
}))

vi.mock("../ReorderSection", () => ({
  ReorderSection: () => null,
}))

vi.mock("../ArchiveTab", () => ({
  ArchiveTab: () => null,
}))

describe("CategoryTabs", () => {
  it("renders Crypto tab when crypto stocks exist", () => {
    const cryptoStock = {
      ticker: "BTC-USD",
      category: "Crypto",
      current_thesis: "monitor btc",
      current_tags: [],
      display_order: 0,
      last_scan_signal: "NORMAL",
      signal_since: null,
      is_active: true,
      is_etf: false,
    } as unknown as RadarStock

    render(
      <CategoryTabs
        stocks={[cryptoStock]}
        totalStocks={[cryptoStock]}
        hasActiveFilters={false}
        removedStocks={[]}
        enrichedMap={{}}
        resonanceMap={{}}
        heldTickers={new Set<string>()}
      />,
    )

    expect(screen.getByText("radar.tab.crypto (1)")).toBeInTheDocument()
  })
})
