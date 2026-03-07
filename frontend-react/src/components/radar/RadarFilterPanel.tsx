import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronDown, CircleHelp } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { SCAN_SIGNAL_ICONS } from "@/lib/constants"
import { getSignalDescription, getSignalLabel } from "@/lib/signal-label"
import { cn } from "@/lib/utils"
import type { ScanSignal } from "@/api/types/radar"
import { DEFAULT_RADAR_FILTERS, FILTER_PRESETS } from "@/hooks/useRadarFilters"
import type { MarketCapBucket, RadarFilterPresetKey, RadarFilterState } from "@/hooks/useRadarFilters"

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

function FilterLabel({ label, tip }: { label: string; tip: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      {label}
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="inline-flex min-h-[28px] min-w-[28px] items-center justify-center rounded-sm text-muted-foreground/60 hover:text-muted-foreground transition-colors"
            aria-label={tip}
          >
            <CircleHelp className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent sideOffset={6} className="max-w-xs">
          {tip}
        </TooltipContent>
      </Tooltip>
    </span>
  )
}

function isPresetActive(filters: RadarFilterState, presetKey: RadarFilterPresetKey): boolean {
  const preset = FILTER_PRESETS.find((item) => item.key === presetKey)
  if (!preset) return false
  const merged = { ...DEFAULT_RADAR_FILTERS, ...preset.filters }
  const sameArray = (left: string[], right: string[]) =>
    left.length === right.length && left.every((item, idx) => item === right[idx])

  return (
    sameArray(filters.signals, merged.signals) &&
    filters.rsiMin === merged.rsiMin &&
    filters.rsiMax === merged.rsiMax &&
    filters.biasMin === merged.biasMin &&
    filters.biasMax === merged.biasMax &&
    filters.volumeRatioMin === merged.volumeRatioMin &&
    filters.volumeRatioMax === merged.volumeRatioMax &&
    sameArray(filters.marketCapBuckets, merged.marketCapBuckets) &&
    filters.peMin === merged.peMin &&
    filters.peMax === merged.peMax &&
    filters.dividendYieldMin === merged.dividendYieldMin &&
    sameArray(filters.sectors, merged.sectors) &&
    sameArray(filters.tags, merged.tags) &&
    filters.heldOnly === merged.heldOnly
  )
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
  applyPreset: (presetKey: RadarFilterPresetKey) => void
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
  applyPreset,
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
        onClick={() => {
          if (!isOpen) {
            setDraft(toDraft(filters))
          }
          onToggleOpen()
        }}
        className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
      >
        <span className="inline-flex items-center gap-2">
          {t("radar.filter.toggle")}
          {activeCountLabel && <Badge variant="secondary" className="text-[10px]">{activeCountLabel}</Badge>}
        </span>
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className="px-4 pb-4 space-y-4">
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">{t("radar.filter.presets")}</p>
            <div className="flex flex-wrap gap-1.5">
              {FILTER_PRESETS.map((preset) => (
                <Tooltip key={preset.key}>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => {
                        applyPreset(preset.key)
                        setDraft(toDraft({ ...DEFAULT_RADAR_FILTERS, ...preset.filters }))
                      }}
                      className={cn(
                        "text-xs px-2.5 py-1.5 rounded-full border min-h-[36px] transition-colors",
                        isPresetActive(filters, preset.key) ? "bg-foreground text-background" : "hover:bg-muted/50",
                      )}
                      aria-pressed={isPresetActive(filters, preset.key)}
                    >
                      {t(`radar.filter.preset.${preset.key}`)}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent sideOffset={6} className="max-w-xs">
                    {t(`radar.filter.preset.${preset.key}_desc`)}
                  </TooltipContent>
                </Tooltip>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <FilterLabel label={t("radar.filter.signal")} tip={t("radar.filter.signal_tip")} />
            <div className="flex flex-wrap gap-1.5">
              {SIGNAL_ORDER.map((signal) => {
                const selected = filters.signals.includes(signal)
                return (
                  <Tooltip key={signal}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => toggleSignal(signal)}
                        className={cn(
                          "text-xs px-2.5 py-1.5 rounded-full border min-h-[36px] transition-colors",
                          selected ? "bg-foreground text-background" : "hover:bg-muted/50",
                        )}
                      >
                        {SCAN_SIGNAL_ICONS[signal] ?? "•"} {getSignalLabel(t, signal)}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent sideOffset={6} className="max-w-xs">
                      {getSignalDescription(t, signal)}
                    </TooltipContent>
                  </Tooltip>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="space-y-1">
              <FilterLabel label={t("radar.filter.rsi")} tip={t("radar.filter.rsi_tip")} />
              <div className="flex gap-2">
                <Input value={draft.rsiMin} onChange={(e) => setDraft((prev) => ({ ...prev, rsiMin: e.target.value }))} placeholder={t("radar.filter.rsi_min_ph")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.rsiMax} onChange={(e) => setDraft((prev) => ({ ...prev, rsiMax: e.target.value }))} placeholder={t("radar.filter.rsi_max_ph")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <FilterLabel label={t("radar.filter.bias")} tip={t("radar.filter.bias_tip")} />
              <div className="flex gap-2">
                <Input value={draft.biasMin} onChange={(e) => setDraft((prev) => ({ ...prev, biasMin: e.target.value }))} placeholder={t("radar.filter.bias_min_ph")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.biasMax} onChange={(e) => setDraft((prev) => ({ ...prev, biasMax: e.target.value }))} placeholder={t("radar.filter.bias_max_ph")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <FilterLabel label={t("radar.filter.volume_ratio")} tip={t("radar.filter.volume_ratio_tip")} />
              <div className="flex gap-2">
                <Input value={draft.volumeRatioMin} onChange={(e) => setDraft((prev) => ({ ...prev, volumeRatioMin: e.target.value }))} placeholder={t("radar.filter.volume_ratio_min_ph")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.volumeRatioMax} onChange={(e) => setDraft((prev) => ({ ...prev, volumeRatioMax: e.target.value }))} placeholder={t("radar.filter.volume_ratio_max_ph")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <FilterLabel label={t("radar.filter.pe")} tip={t("radar.filter.pe_tip")} />
              <div className="flex gap-2">
                <Input value={draft.peMin} onChange={(e) => setDraft((prev) => ({ ...prev, peMin: e.target.value }))} placeholder={t("radar.filter.pe_min_ph")} className="h-8 text-xs" inputMode="decimal" />
                <Input value={draft.peMax} onChange={(e) => setDraft((prev) => ({ ...prev, peMax: e.target.value }))} placeholder={t("radar.filter.pe_max_ph")} className="h-8 text-xs" inputMode="decimal" />
              </div>
            </div>
            <div className="space-y-1">
              <FilterLabel label={t("radar.filter.dividend_yield")} tip={t("radar.filter.dividend_yield_tip")} />
              <Input value={draft.dividendYieldMin} onChange={(e) => setDraft((prev) => ({ ...prev, dividendYieldMin: e.target.value }))} placeholder={t("radar.filter.dividend_yield_min_ph")} className="h-8 text-xs" inputMode="decimal" />
            </div>
          </div>

          <div className="space-y-2">
            <FilterLabel label={t("radar.filter.market_cap")} tip={t("radar.filter.market_cap_tip")} />
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
              <FilterLabel label={t("radar.filter.sector")} tip={t("radar.filter.sector_tip")} />
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
              <FilterLabel label={t("radar.filter.tags")} tip={t("radar.filter.tags_tip")} />
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
