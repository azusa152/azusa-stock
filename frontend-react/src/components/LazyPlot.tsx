import { lazy, Suspense } from "react"
import type { PlotParams } from "react-plotly.js"

const Plot = lazy(() => import("react-plotly.js"))

/** Lazy-loaded Plotly wrapper — keeps Plotly out of the initial JS bundle. */
export function LazyPlot(props: PlotParams) {
  return (
    <Suspense fallback={<div style={{ height: props.layout?.height ?? 200 }} />}>
      <Plot {...props} />
    </Suspense>
  )
}
