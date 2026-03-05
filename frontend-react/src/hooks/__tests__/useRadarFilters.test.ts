import { describe, expect, it } from "vitest"
import { renderHook, act } from "@testing-library/react"
import type { RadarEnrichedStock, RadarStock } from "@/api/types/radar"
import { DEFAULT_RADAR_FILTERS, filterStocks, useRadarFilters } from "../useRadarFilters"

function makeStock(ticker: string, overrides: Partial<RadarStock> = {}): RadarStock {
  return {
    ticker,
    category: "Growth",
    current_thesis: "test thesis",
    current_tags: [],
    display_order: 0,
    last_scan_signal: "NORMAL",
    signal_since: null,
    is_active: true,
    is_etf: false,
    signals: null,
    ...overrides,
  }
}

describe("filterStocks", () => {
  const stocks: RadarStock[] = [
    makeStock("AAA", { current_tags: ["AI", "Cloud"], last_scan_signal: "OVERSOLD" }),
    makeStock("BBB", { current_tags: ["Dividend"], last_scan_signal: "CAUTION_HIGH" }),
    makeStock("CCC", { current_tags: [], last_scan_signal: "NORMAL" }),
  ]

  const enrichedMap: Record<string, RadarEnrichedStock> = {
    AAA: {
      ticker: "AAA",
      computed_signal: "DEEP_VALUE",
      rsi: 22,
      bias: -25,
      volume_ratio: 1.8,
      market_cap: 1_000_000_000,
      trailing_pe: 10,
      sector: "Technology",
      dividend: { dividend_yield: 0.01 },
    },
    BBB: {
      ticker: "BBB",
      computed_signal: "CAUTION_HIGH",
      rsi: 75,
      bias: 15,
      volume_ratio: 1.1,
      market_cap: 15_000_000_000,
      trailing_pe: 28,
      sector: "Financial Services",
      dividend: { dividend_yield: 0.04 },
    },
    CCC: {
      ticker: "CCC",
      computed_signal: "NORMAL",
      rsi: undefined,
      bias: undefined,
      volume_ratio: undefined,
      market_cap: 200_000_000_000,
      trailing_pe: undefined,
      sector: "Technology",
      dividend: { dividend_yield: undefined },
    },
  }

  const heldTickers = new Set(["AAA", "CCC"])

  it("returns all stocks when no filters are active", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, DEFAULT_RADAR_FILTERS)
    expect(result.map((s) => s.ticker)).toEqual(["AAA", "BBB", "CCC"])
  })

  it("filters by selected signal", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      signals: ["DEEP_VALUE"],
    })
    expect(result.map((s) => s.ticker)).toEqual(["AAA"])
  })

  it("filters by RSI range and excludes null RSI when active", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      rsiMin: 20,
      rsiMax: 60,
    })
    expect(result.map((s) => s.ticker)).toEqual(["AAA"])
  })

  it("filters by market cap bucket", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      marketCapBuckets: ["large"],
    })
    expect(result.map((s) => s.ticker)).toEqual(["BBB"])
  })

  it("treats 200B market cap as mega bucket boundary", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      marketCapBuckets: ["mega"],
    })
    expect(result.map((s) => s.ticker)).toEqual(["CCC"])
  })

  it("filters by bias range", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      biasMin: -30,
      biasMax: -20,
    })
    expect(result.map((s) => s.ticker)).toEqual(["AAA"])
  })

  it("filters by minimum dividend yield", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      dividendYieldMin: 0.03,
    })
    expect(result.map((s) => s.ticker)).toEqual(["BBB"])
  })

  it("filters by tags using overlap", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      tags: ["Cloud"],
    })
    expect(result.map((s) => s.ticker)).toEqual(["AAA"])
  })

  it("filters by held-only toggle", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      heldOnly: true,
    })
    expect(result.map((s) => s.ticker)).toEqual(["AAA", "CCC"])
  })

  it("supports combined filters", () => {
    const result = filterStocks(stocks, enrichedMap, heldTickers, {
      ...DEFAULT_RADAR_FILTERS,
      sectors: ["Technology"],
      peMin: 5,
      peMax: 20,
      volumeRatioMin: 1.5,
      heldOnly: true,
    })
    expect(result.map((s) => s.ticker)).toEqual(["AAA"])
  })
})

describe("useRadarFilters", () => {
  it("tracks active filter count and can reset filters", () => {
    const { result } = renderHook(() => useRadarFilters())

    act(() => {
      result.current.toggleSignal("DEEP_VALUE")
      result.current.setFilter("heldOnly", true)
    })
    expect(result.current.activeFilterCount).toBe(2)

    act(() => {
      result.current.resetFilters()
    })
    expect(result.current.activeFilterCount).toBe(0)
    expect(result.current.filters).toEqual(DEFAULT_RADAR_FILTERS)
  })

  it("applies presets by resetting first and then setting preset filters", () => {
    const { result } = renderHook(() => useRadarFilters())

    act(() => {
      result.current.setFilter("heldOnly", true)
      result.current.setFilter("rsiMin", 20)
      result.current.applyPreset("income")
    })

    expect(result.current.filters.heldOnly).toBe(false)
    expect(result.current.filters.rsiMin).toBeNull()
    expect(result.current.filters.dividendYieldMin).toBe(0.03)
    expect(result.current.filters.marketCapBuckets).toEqual(["large", "mega"])
    expect(result.current.activeFilterCount).toBe(2)
  })
})
