import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { SCAN_SIGNAL_ICONS } from "@/lib/constants"
import { getSignalLabel } from "@/lib/signal-label"
import { cn } from "@/lib/utils"
import type { ScanSignal } from "@/api/types/radar"
import { DEFAULT_RADAR_FILTERS } from "@/hooks/useRadarFilters"
import type { MarketCapBucket, RadarFilterState } from "@/hooks/useRadarFilters"

const SIGNAL_ORDER: ScanSignal[] = [
  "DEEP_VALUE",
  "OVERSOLD",
  "CONTRARIAN_BUY",
  "APPROACHING_BUY",
  "OVERHEATED",
  "CAUTION_HIGH",
  "WEAKENING",
  "THESIS_BROKEN",
  "NORMAL",
]

const MARKET_CAP_BUCKETS: MarketCapBucket[] = ["small", "mid", "large", "mega"]

type NumericDraftState = {
  rsiMin: string
  rsiMax: string
  biasMin: string
  biasMax: string
  volumeRatioMin: string
  volumeRatioMax: string
  peMin: string
  peMax: string
  dividendYieldMin: string
}

function toDraft(filters: RadarFilterState): NumericDraftState {
  return {
    rsiMin: filters.rsiMin?.toString() ?? "",
    rsiMax: filters.rsiMax?.toString() ?? "",
    biasMin: filters.biasMin?.toString() ?? "",
    biasMax: filters.biasMax?.toString() ?? "",
    volumeRatioMin: filters.volumeRatioMin?.toString() ?? "",
    volumeRatioMax: filters.volumeRatioMax?.toString() ?? "",
    peMin: filters.peMin?.toString() ?? "",
    peMax: filters.peMax?.toString() ?? "",
    dividendYieldMin: filters.dividendYieldMin?.toString() ?? "",
  }
}

function parseNullableNumber(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number(trimmed)
  return Number.isNaN(parsed) ? null : parsed
}

interface Props {
  isOpen: boolean
  onToggleOpen: () => void
  filters: RadarFilterState
  activeFilterCount: number
  availableSectors: string[]
  availableTags: string[]
  setFilter: <K extends keyof RadarFilterState>(key: K, value: RadarFilterState[K]) => void
  toggleSignal: (signal: ScanSignal) => void
  toggleSector: (sector: string) => void
  toggleTag: (tag: string) => void
  toggleMarketCapBucket: (bucket: MarketCapBucket) => void
  resetFilters: () => void
}

export function RadarFilterPanel({
  isOpen,
  onToggleOpen,
  filters,
  activeFilterCount,
  availableSectors,
  availableTags,
  setFilter,
  toggleSignal,
  toggleSector,
  toggleTag,
  toggleMarketCapBucket,
  resetFilters,
}: Props) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<NumericDraftState>(() => toDraft(filters))
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      const nextValues = {
        rsiMin: parseNullableNumber(draft.rsiMin),
        rsiMax: parseNullableNumber(draft.rsiMax),
        biasMin: parseNullableNumber(draft.biasMin),
        biasMax: parseNullableNumber(draft.biasMax),
        volumeRatioMin: parseNullableNumber(draft.volumeRatioMin),
        volumeRatioMax: parseNullableNumber(draft.volumeRatioMax),
        peMin: parseNullableNumber(draft.peMin),
        peMax: parseNullableNumber(draft.peMax),
        dividendYieldMin: parseNullableNumber(draft.dividendYieldMin),
      }
      if (nextValues.rsiMin !== filters.rsiMin) setFilter("rsiMin", nextValues.rsiMin)
      if (nextValues.rsiMax !== filters.rsiMax) setFilter("rsiMax", nextValues.rsiMax)
      if (nextValues.biasMin !== filters.biasMin) setFilter("biasMin", nextValues.biasMin)
      if (nextValues.biasMax !== filters.biasMax) setFilter("biasMax", nextValues.biasMax)
      if (nextValues.volumeRatioMin !== filters.volumeRatioMin) setFilter("volumeRatioMin", nextValues.volumeRatioMin)
      if (nextValues.volumeRatioMax !== filters.volumeRatioMax) setFilter("volumeRatioMax", nextValues.volumeRatioMax)
      if (nextValues.peMin !== filters.peMin) setFilter("peMin", nextValues.peMin)
      if (nextValues.peMax !== filters.peMax) setFilter("peMax", nextValues.peMax)
      if (nextValues.dividendYieldMin !== filters.dividendYieldMin) setFilter("dividendYieldMin", nextValues.dividendYieldMin)
    }, 300)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [
    draft,
    filters.rsiMin,
    filters.rsiMax,
    filters.biasMin,
    filters.biasMax,
    filters.volumeRatioMin,
    filters.volumeRatioMax,
    filters.peMin,
    filters.peMax,
    filters.dividendYieldMin,
    setFilter,
  ])

  const hasTags = availableTags.length > 0
  const hasSectors = availableSectors.length > 0
  const clearDisabled = activeFilterCount === 0

  const activeCountLabel = useMemo(() => {
    if (activeFilterCount === 0) return null
    return t("radar.filter.active_count", { count: activeFilterCount })
  }, [activeFilterCount, t])

  return (
    <div className="rounded-md border border-border">
      <button
        onClick={onToggleOpen}
        className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
      >
        <span className="inline-flex items-center gap-2">
          {t("radar.filter.toggle")}
          {activeCountLabel && <Badge variant="secondary" className="text-[10px]">{activeCountLabel}</Badge>}
        </span>
        <span className="text-muted-foreground text-xs">{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-4">
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">{t("radar.filter.signal")}</p>
            <div className="flex flex-wrap gap-1.5">
              {SIGNAL_ORDER.map((signal) => {
                const selected = filters.signals.includes(signal)
                return (
                  <button
                    key={signal}
                    onClick={() => toggleSignal(signal)}
                    className={cn(
                      "text-xs px-2.5 py-1.5 rounded-full border min-h-[36px] transition-colors",
                      selected ? "bg-foreground text-background" : "hover:bg-muted/50",
                    )}
                  >
                    {SCAN_SIGNAL_ICONS[signal] ?? "•"} {getSignalLabel(t, signal)}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t("radar.filter.rsi")}</p>
              <div className="flex gap-2">
                <Input value={draft.rsiMin} onChange={(e) => setDraft((prev) => ({ ...prev, rsiMin: e.target.value }))} placeholder={t("radar.filter.min")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.rsiMax} onChange={(e) => setDraft((prev) => ({ ...prev, rsiMax: e.target.value }))} placeholder={t("radar.filter.max")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t("radar.filter.bias")}</p>
              <div className="flex gap-2">
                <Input value={draft.biasMin} onChange={(e) => setDraft((prev) => ({ ...prev, biasMin: e.target.value }))} placeholder={t("radar.filter.min")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.biasMax} onChange={(e) => setDraft((prev) => ({ ...prev, biasMax: e.target.value }))} placeholder={t("radar.filter.max")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t("radar.filter.volume_ratio")}</p>
              <div className="flex gap-2">
                <Input value={draft.volumeRatioMin} onChange={(e) => setDraft((prev) => ({ ...prev, volumeRatioMin: e.target.value }))} placeholder={t("radar.filter.min")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.volumeRatioMax} onChange={(e) => setDraft((prev) => ({ ...prev, volumeRatioMax: e.target.value }))} placeholder={t("radar.filter.max")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t("radar.filter.pe")}</p>
              <div className="flex gap-2">
                <Input value={draft.peMin} onChange={(e) => setDraft((prev) => ({ ...prev, peMin: e.target.value }))} placeholder={t("radar.filter.min")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.peMax} onChange={(e) => setDraft((prev) => ({ ...prev, peMax: e.target.value }))} placeholder={t("radar.filter.max")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t("radar.filter.dividend_yield")}</p>
              <Input value={draft.dividendYieldMin} onChange={(e) => setDraft((prev) => ({ ...prev, dividendYieldMin: e.target.value }))} placeholder={t("radar.filter.min")} className="h-8 text-xs" inputMode="decimal" />
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">{t("radar.filter.market_cap")}</p>
            <div className="flex flex-wrap gap-1.5">
              {MARKET_CAP_BUCKETS.map((bucket) => {
                const selected = filters.marketCapBuckets.includes(bucket)
                return (
                  <button
                    key={bucket}
                    onClick={() => toggleMarketCapBucket(bucket)}
                    className={cn(
                      "text-xs px-2.5 py-1.5 rounded-full border min-h-[36px] transition-colors",
                      selected ? "bg-foreground text-background" : "hover:bg-muted/50",
                    )}
                  >
                    {t(`radar.filter.cap_${bucket}`)}
                  </button>
                )
              })}
            </div>
          </div>

          {hasSectors && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">{t("radar.filter.sector")}</p>
              <div className="flex flex-wrap gap-1.5">
                {availableSectors.map((sector) => {
                  const selected = filters.sectors.includes(sector)
                  return (
                    <button
                      key={sector}
                      onClick={() => toggleSector(sector)}
                      className={cn(
                        "text-xs px-2.5 py-1.5 rounded-full border min-h-[36px] transition-colors",
                        selected ? "bg-foreground text-background" : "hover:bg-muted/50",
                      )}
                    >
                      {sector}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {hasTags && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">{t("radar.filter.tags")}</p>
              <div className="flex flex-wrap gap-1.5">
                {availableTags.map((tag) => {
                  const selected = filters.tags.includes(tag)
                  return (
                    <button
                      key={tag}
                      onClick={() => toggleTag(tag)}
                      className={cn(
                        "text-xs px-2.5 py-1.5 rounded-full border min-h-[36px] transition-colors",
                        selected ? "bg-foreground text-background" : "hover:bg-muted/50",
                      )}
                    >
                      #{tag}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
            <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
              <Switch checked={filters.heldOnly} onCheckedChange={(checked) => setFilter("heldOnly", checked)} />
              {t("radar.filter.held_only")}
            </label>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                resetFilters()
                setDraft(toDraft(DEFAULT_RADAR_FILTERS))
              }}
              disabled={clearDisabled}
            >
              {t("radar.filter.clear_all")}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
