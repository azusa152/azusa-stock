import { useMemo } from "react"
import { ColorType } from "lightweight-charts"
import { useTheme } from "./useTheme"

export interface LightweightChartTheme {
  background: { type: typeof ColorType.Solid; color: string }
  textColor: string
  gridColor: string
  borderColor: string
}

/** Returns lightweight-charts layout colors that respect dark/light theme. */
export function useLightweightChartTheme(): LightweightChartTheme {
  const { theme } = useTheme()
  const isDark = theme === "dark"

  return useMemo(
    () => ({
      background: {
        type: ColorType.Solid as const,
        color: "rgba(0,0,0,0)",
      },
      textColor: isDark ? "#9ca3af" : "#6b7280",
      gridColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
      borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
    }),
    [isDark],
  )
}
