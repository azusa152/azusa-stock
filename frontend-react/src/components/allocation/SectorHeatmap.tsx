import { useTranslation } from "react-i18next"
import { Treemap, Tooltip, ResponsiveContainer } from "recharts"
import type { SectorExposureItem } from "@/api/types/allocation"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { CHART_COLOR_PALETTE } from "@/lib/constants"

interface Props {
  data: SectorExposureItem[]
}

const SECTOR_COLORS = [...CHART_COLOR_PALETTE, "#14b8a6", "#f43f5e", "#6366f1"]

interface ContentProps {
  x?: number; y?: number; width?: number; height?: number
  name?: string; weight_pct?: number; colorIdx?: number
}

function SectorCell({ x = 0, y = 0, width = 0, height = 0, name, weight_pct, colorIdx = 0 }: ContentProps) {
  const fill = SECTOR_COLORS[colorIdx % SECTOR_COLORS.length]
  if (width < 10 || height < 10) return null
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} rx={3} />
      {width > 50 && height > 28 && (
        <text x={x + width / 2} y={y + height / 2 - 5} textAnchor="middle" fill="#fff" fontSize={10} fontWeight={500}>
          {name}
        </text>
      )}
      {width > 50 && height > 28 && typeof weight_pct === "number" && (
        <text x={x + width / 2} y={y + height / 2 + 9} textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize={9}>
          {weight_pct.toFixed(1)}%
        </text>
      )}
    </g>
  )
}

export function SectorHeatmap({ data }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  if (!data || data.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.sector.title")}</p>
        <p className="text-sm text-muted-foreground">{t("allocation.sector.empty")}</p>
      </div>
    )
  }

  const chartData = data.map((d, i) => ({
    name: d.sector,
    size: d.value,
    weight_pct: d.weight_pct,
    colorIdx: i,
  }))

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.sector.title")}</p>
      <ResponsiveContainer width="100%" height={250}>
        <Treemap
          data={chartData}
          dataKey="size"
          content={<SectorCell />}
        >
          <Tooltip
            contentStyle={theme.tooltipStyle}
            formatter={(_v: number | undefined, _name: unknown, props: { payload?: { weight_pct?: number; name?: string } }) => [
              `${typeof props.payload?.weight_pct === "number" ? props.payload.weight_pct.toFixed(1) : ""}%`,
              props.payload?.name ?? "",
            ]}
          />
        </Treemap>
      </ResponsiveContainer>
    </div>
  )
}
