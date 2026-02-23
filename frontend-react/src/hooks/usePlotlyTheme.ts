import { useTheme } from "./useTheme"

/** Returns Plotly layout overrides that respect the current dark/light theme. */
export function usePlotlyTheme() {
  const { theme } = useTheme()
  const isDark = theme === "dark"

  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: isDark ? "#e5e7eb" : "#1f2937" },
  } as const
}
