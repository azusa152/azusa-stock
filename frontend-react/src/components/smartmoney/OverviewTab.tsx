import { useTranslation } from "react-i18next"
import { Skeleton } from "@/components/ui/skeleton"
import { useGuruDashboard } from "@/api/hooks/useSmartMoney"
import { GuruStatusCards } from "./GuruStatusCards"
import { SeasonHighlights } from "./SeasonHighlights"
import { ActivityFeed } from "./ActivityFeed"
import { ConsensusStocks } from "./ConsensusStocks"
import { SectorChart } from "./SectorChart"

export function OverviewTab({ style }: { style?: string | null }) {
  const { t } = useTranslation()
  const { data, isLoading } = useGuruDashboard(style)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-40" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">{t("smart_money.overview.no_data")}</p>
  }

  return (
    <div className="space-y-6">
      {/* Guru status cards */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.overview.guru_cards_header")}</p>
        <GuruStatusCards gurus={data.gurus} />
      </section>

      {/* Season highlights */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.overview.highlights_header")}</p>
        <SeasonHighlights data={data.season_highlights} />
      </section>

      {/* Activity feed */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.overview.activity_header")}</p>
        <ActivityFeed data={data.activity_feed} />
      </section>

      {/* Consensus holdings */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.overview.consensus_header")}</p>
        <ConsensusStocks items={data.consensus} />
      </section>

      {/* Sector allocation */}
      <section>
        <p className="text-sm font-semibold mb-2">{t("smart_money.overview.sector_header")}</p>
        <SectorChart data={data.sector_breakdown} />
      </section>
    </div>
  )
}
