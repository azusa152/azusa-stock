import { Skeleton } from "@/components/ui/skeleton"
import type { FxHistoryPoint } from "@/api/types/fxWatch"

interface Props {
  data: FxHistoryPoint[] | undefined
  width?: number
  height?: number
}

export function FxSparkline({ data, width = 80, height = 32 }: Props) {
  if (data === undefined) {
    return <Skeleton style={{ width, height }} className="rounded" />
  }
  if (data.length < 2) return null

  const slice = data.slice(-30)
  const values = slice.map((d) => d.close)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const isUp = values[values.length - 1] >= values[0]
  const color = isUp ? "#22c55e" : "#ef4444"

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width
      const y = height - ((v - min) / range) * (height - 4) - 2
      return `${x},${y}`
    })
    .join(" ")

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="shrink-0"
      aria-hidden="true"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}
