import { useTranslation } from "react-i18next"
import { Skeleton } from "@/components/ui/skeleton"
import { useAllocRebalance } from "@/api/hooks/useAllocation"
import { HealthScore } from "./HealthScore"
import { AllocationCharts } from "./AllocationCharts"
import { DriftChart } from "./DriftChart"
import { HoldingsTable } from "../holdings/HoldingsTable"
import { XRayOverlap } from "./XRayOverlap"
import { SectorHeatmap } from "./SectorHeatmap"

interface Props {
  displayCurrency: string
  privacyMode: boolean
  enabled: boolean
}

export function RebalanceAnalysis({ displayCurrency, privacyMode, enabled }: Props) {
  const { t } = useTranslation()
  const { data, isLoading } = useAllocRebalance(displayCurrency, enabled)

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">{t("allocation.loading")}</p>
  }

  return (
    <div className="space-y-6">
      {/* Health score */}
      <HealthScore
        score={data.health_score}
        level={data.health_level}
        calculatedAt={data.calculated_at}
      />

      {/* Rebalance advice */}
      {data.advice && data.advice.length > 0 && (
        <section className="space-y-1">
          <p className="text-sm font-semibold">{t("allocation.health.advice_title")}</p>
          <ul className="space-y-1">
            {data.advice.map((a, i) => (
              <li key={i} className="text-xs text-muted-foreground">• {a}</li>
            ))}
          </ul>
        </section>
      )}

      <hr className="border-border" />

      {/* Allocation charts */}
      <AllocationCharts categories={data.categories} />

      <hr className="border-border" />

      {/* Drift chart */}
      <DriftChart categories={data.categories} />

      <hr className="border-border" />

      {/* Holdings detail table */}
      <HoldingsTable holdings={data.holdings_detail} privacyMode={privacyMode} />

      <hr className="border-border" />

      {/* X-Ray overlap */}
      {data.xray && data.xray.length > 0 && (
        <>
          <XRayOverlap xray={data.xray} />
          <hr className="border-border" />
        </>
      )}

      {/* Sector heatmap */}
      {data.sector_exposure && (
        <SectorHeatmap data={data.sector_exposure} />
      )}
    </div>
  )
}
