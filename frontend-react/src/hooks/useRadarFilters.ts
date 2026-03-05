import { useCallback, useMemo, useState } from "react"
import type { RadarEnrichedStock, RadarStock, ScanSignal } from "@/api/types/radar"

export type MarketCapBucket = "small" | "mid" | "large" | "mega"

export interface RadarFilterState {
  signals: ScanSignal[]
  rsiMin: number | null
  rsiMax: number | null
  biasMin: number | null
  biasMax: number | null
  volumeRatioMin: number | null
  volumeRatioMax: number | null
  marketCapBuckets: MarketCapBucket[]
  peMin: number | null
  peMax: number | null
  dividendYieldMin: number | null
  sectors: string[]
  tags: string[]
  heldOnly: boolean
}

export type RadarFilterPresetKey = "income" | "bargain" | "bluechip"

export interface RadarFilterPreset {
  key: RadarFilterPresetKey
  filters: Partial<RadarFilterState>
}

export const DEFAULT_RADAR_FILTERS: RadarFilterState = {
  signals: [],
  rsiMin: null,
  rsiMax: null,
  biasMin: null,
  biasMax: null,
  volumeRatioMin: null,
  volumeRatioMax: null,
  marketCapBuckets: [],
  peMin: null,
  peMax: null,
  dividendYieldMin: null,
  sectors: [],
  tags: [],
  heldOnly: false,
}

export const FILTER_PRESETS: RadarFilterPreset[] = [
  {
    key: "income",
    filters: {
      dividendYieldMin: 0.03,
      marketCapBuckets: ["large", "mega"],
    },
  },
  {
    key: "bargain",
    filters: {
      signals: ["DEEP_VALUE", "OVERSOLD", "CONTRARIAN_BUY"],
    },
  },
  {
    key: "bluechip",
    filters: {
      marketCapBuckets: ["large", "mega"],
      signals: ["NORMAL"],
    },
  },
]

function inRange(value: number | null | undefined, min: number | null, max: number | null): boolean {
  if (min == null && max == null) return true
  if (value == null) return false
  if (min != null && value < min) return false
  if (max != null && value > max) return false
  return true
}

function toMarketCapBucket(value: number | null | undefined): MarketCapBucket | null {
  if (value == null || Number.isNaN(value)) return null
  if (value < 2_000_000_000) return "small"
  if (value < 10_000_000_000) return "mid"
  if (value < 200_000_000_000) return "large"
  return "mega"
}

function getTags(stock: RadarStock): string[] {
  return (stock.current_tags ?? []).map((tag) => tag.trim()).filter(Boolean)
}

function hasOverlap(left: string[], right: string[]): boolean {
  if (!left.length || !right.length) return false
  const rightSet = new Set(right.map((item) => item.toLowerCase()))
  return left.some((item) => rightSet.has(item.toLowerCase()))
}

export function filterStocks(
  stocks: RadarStock[],
  enrichedMap: Record<string, RadarEnrichedStock>,
  heldTickers: Set<string>,
  filters: RadarFilterState,
): RadarStock[] {
  return stocks.filter((stock) => {
    const enrichment = enrichedMap[stock.ticker]
    const signal = enrichment?.computed_signal ?? enrichment?.last_scan_signal ?? stock.last_scan_signal
    const rsi = enrichment?.rsi ?? enrichment?.signals?.rsi
    const bias = enrichment?.bias ?? enrichment?.signals?.bias
    const volumeRatio = enrichment?.volume_ratio ?? enrichment?.signals?.volume_ratio
    const marketCap = enrichment?.market_cap ?? enrichment?.fundamentals?.market_cap
    const trailingPe = enrichment?.trailing_pe ?? enrichment?.fundamentals?.trailing_pe
    const dividendYield = enrichment?.dividend?.dividend_yield
    const sector = enrichment?.sector?.trim()
    const isHeld = heldTickers.has(stock.ticker.toUpperCase())
    const stockTags = getTags(stock)

    if (filters.signals.length > 0 && (!signal || !filters.signals.includes(signal))) return false
    if (!inRange(rsi, filters.rsiMin, filters.rsiMax)) return false
    if (!inRange(bias, filters.biasMin, filters.biasMax)) return false
    if (!inRange(volumeRatio, filters.volumeRatioMin, filters.volumeRatioMax)) return false
    if (!inRange(trailingPe, filters.peMin, filters.peMax)) return false
    if (filters.dividendYieldMin != null && (dividendYield == null || dividendYield < filters.dividendYieldMin)) return false
    if (filters.marketCapBuckets.length > 0) {
      const bucket = toMarketCapBucket(marketCap)
      if (!bucket || !filters.marketCapBuckets.includes(bucket)) return false
    }
    if (filters.sectors.length > 0 && (!sector || !filters.sectors.includes(sector))) return false
    if (filters.tags.length > 0 && !hasOverlap(stockTags, filters.tags)) return false
    if (filters.heldOnly && !isHeld) return false

    return true
  })
}

function countActiveFilters(filters: RadarFilterState): number {
  return [
    filters.signals.length > 0,
    filters.rsiMin != null || filters.rsiMax != null,
    filters.biasMin != null || filters.biasMax != null,
    filters.volumeRatioMin != null || filters.volumeRatioMax != null,
    filters.marketCapBuckets.length > 0,
    filters.peMin != null || filters.peMax != null,
    filters.dividendYieldMin != null,
    filters.sectors.length > 0,
    filters.tags.length > 0,
    filters.heldOnly,
  ].filter(Boolean).length
}

export function useRadarFilters() {
  const [filters, setFilters] = useState<RadarFilterState>(DEFAULT_RADAR_FILTERS)

  const setFilter = useCallback(<K extends keyof RadarFilterState>(key: K, value: RadarFilterState[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  const toggleSignal = useCallback((signal: ScanSignal) => {
    setFilters((prev) => ({
      ...prev,
      signals: prev.signals.includes(signal) ? prev.signals.filter((s) => s !== signal) : [...prev.signals, signal],
    }))
  }, [])

  const toggleSector = useCallback((sector: string) => {
    setFilters((prev) => ({
      ...prev,
      sectors: prev.sectors.includes(sector) ? prev.sectors.filter((s) => s !== sector) : [...prev.sectors, sector],
    }))
  }, [])

  const toggleTag = useCallback((tag: string) => {
    setFilters((prev) => ({
      ...prev,
      tags: prev.tags.includes(tag) ? prev.tags.filter((t) => t !== tag) : [...prev.tags, tag],
    }))
  }, [])

  const toggleMarketCapBucket = useCallback((bucket: MarketCapBucket) => {
    setFilters((prev) => ({
      ...prev,
      marketCapBuckets: prev.marketCapBuckets.includes(bucket)
        ? prev.marketCapBuckets.filter((b) => b !== bucket)
        : [...prev.marketCapBuckets, bucket],
    }))
  }, [])

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_RADAR_FILTERS)
  }, [])

  const applyPreset = useCallback((presetKey: RadarFilterPresetKey) => {
    const preset = FILTER_PRESETS.find((item) => item.key === presetKey)
    if (!preset) return
    setFilters({
      ...DEFAULT_RADAR_FILTERS,
      ...preset.filters,
    })
  }, [])

  const activeFilterCount = useMemo(() => countActiveFilters(filters), [filters])

  return {
    filters,
    setFilter,
    toggleSignal,
    toggleSector,
    toggleTag,
    toggleMarketCapBucket,
    resetFilters,
    applyPreset,
    activeFilterCount,
  }
}
