import { useMemo } from "react"
import { useTheme } from "./useTheme"

export interface RechartsTheme {
  tickColor: string
  gridColor: string
  tooltipBg: string
  tooltipBorder: string
  tooltipText: string
  tooltipStyle: React.CSSProperties
}

/** Returns Recharts color tokens that respect dark/light theme. */
export function useRechartsTheme(): RechartsTheme {
  const { theme } = useTheme()
  const isDark = theme === "dark"

  return useMemo(() => {
    const tooltipBg = isDark ? "#1f2937" : "#ffffff"
    const tooltipBorder = isDark ? "#374151" : "#e5e7eb"
    const tooltipText = isDark ? "#f9fafb" : "#111827"

    return {
      tickColor: isDark ? "#9ca3af" : "#6b7280",
      gridColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
      tooltipBg,
      tooltipBorder,
      tooltipText,
      tooltipStyle: {
        backgroundColor: tooltipBg,
        border: `1px solid ${tooltipBorder}`,
        borderRadius: 6,
        fontSize: 11,
        color: tooltipText,
      } as React.CSSProperties,
    }
  }, [isDark])
}
