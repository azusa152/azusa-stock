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

export function CategoryTabs({ stocks, removedStocks, enrichedMap, resonanceMap }: Props) {
  const { t } = useTranslation()

  const activeStocks = stocks.filter((s) => s.is_active)
  const categoryMap = Object.fromEntries(
    RADAR_CATEGORIES.map((cat) => [cat, activeStocks.filter((s) => s.category === cat)]),
  ) as Record<StockCategory, RadarStock[]>

  const tabLabelKey: Record<string, string> = {
    Trend_Setter: "radar.tab.trend_setter",
    Moat: "radar.tab.moat",
    Growth: "radar.tab.growth",
    Bond: "radar.tab.bond",
  }

  return (
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
  )
}
