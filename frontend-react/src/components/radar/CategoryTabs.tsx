import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CATEGORY_ICON_SHORT, RADAR_CATEGORIES } from "@/lib/constants"
import { StockCard } from "./StockCard"
import { ReorderSection } from "./ReorderSection"
import { ArchiveTab } from "./ArchiveTab"
import type { RadarStock, RemovedStock, RadarEnrichedStock, ResonanceMap, StockCategory } from "@/api/types/radar"

interface Props {
  stocks: RadarStock[]
  removedStocks: RemovedStock[]
  enrichedMap: Record<string, RadarEnrichedStock>
  resonanceMap: ResonanceMap
}

function inferMarket(ticker: string): string {
  if (ticker.endsWith(".T")) return "JP"
  if (ticker.endsWith(".TW")) return "TW"
  if (ticker.endsWith(".HK")) return "HK"
  return "US"
}

export function CategoryTabs({ stocks, removedStocks, enrichedMap, resonanceMap }: Props) {
  const { t } = useTranslation()
  const [selectedMarket, setSelectedMarket] = useState("ALL")

  const activeStocks = stocks.filter((s) => s.is_active)

  // Derive available markets from active stocks
  const markets = useMemo(() => {
    const set = new Set(activeStocks.map((s) => inferMarket(s.ticker)))
    return ["ALL", ...Array.from(set).sort()]
  }, [activeStocks])

  // Apply market filter
  const filteredStocks = useMemo(
    () =>
      selectedMarket === "ALL"
        ? activeStocks
        : activeStocks.filter((s) => inferMarket(s.ticker) === selectedMarket),
    [activeStocks, selectedMarket],
  )

  const categoryMap = Object.fromEntries(
    RADAR_CATEGORIES.map((cat) => [cat, filteredStocks.filter((s) => s.category === cat)]),
  ) as Record<StockCategory, RadarStock[]>

  const tabLabelKey: Record<string, string> = {
    Trend_Setter: "radar.tab.trend_setter",
    Moat: "radar.tab.moat",
    Growth: "radar.tab.growth",
    Bond: "radar.tab.bond",
  }

  return (
    <div className="space-y-3">
      {/* Market filter pills — only shown when more than one market is present */}
      {markets.length > 2 && (
        <div className="flex flex-wrap gap-1">
          {markets.map((m) => (
            <button
              key={m}
              onClick={() => setSelectedMarket(m)}
              className={`px-2 py-0.5 rounded text-xs border transition-colors ${
                selectedMarket === m
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-transparent text-muted-foreground border-border hover:bg-muted/40"
              }`}
            >
              {m === "ALL" ? t("radar.market.all") : m}
            </button>
          ))}
        </div>
      )}

      <Tabs defaultValue="Trend_Setter">
        <TabsList className="flex-wrap h-auto gap-1">
          {RADAR_CATEGORIES.map((cat) => (
            <TabsTrigger key={cat} value={cat} className="text-xs">
              {t(tabLabelKey[cat], { count: categoryMap[cat]?.length ?? 0 })}
            </TabsTrigger>
          ))}
          <TabsTrigger value="archive" className="text-xs">
            {t("radar.tab.removed", { count: removedStocks.length })}
          </TabsTrigger>
        </TabsList>

        {RADAR_CATEGORIES.map((cat) => (
          <TabsContent key={cat} value={cat} className="mt-4 space-y-2">
            {categoryMap[cat]?.length ? (
              <>
                <ReorderSection stocks={categoryMap[cat]} />
                {categoryMap[cat].map((stock) => (
                  <StockCard
                    key={stock.ticker}
                    stock={stock}
                    enrichment={enrichedMap[stock.ticker]}
                    resonance={resonanceMap[stock.ticker]}
                  />
                ))}
              </>
            ) : (
              <p className="text-sm text-muted-foreground py-4">
                {t("radar.empty_category", { category: `${CATEGORY_ICON_SHORT[cat] ?? ""} ${cat.replace("_", " ")}` })}
              </p>
            )}
          </TabsContent>
        ))}

        <TabsContent value="archive" className="mt-4">
          <ArchiveTab removedStocks={removedStocks} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
