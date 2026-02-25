import { describe, it, expect, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { ColorType } from "lightweight-charts"
import { useTheme } from "../useTheme"
import { useLightweightChartTheme } from "../useLightweightChartTheme"
import { useRechartsTheme } from "../useRechartsTheme"

beforeEach(() => {
  useTheme.setState({ theme: "light" })
})

describe("useLightweightChartTheme", () => {
  it("returns a solid background type", () => {
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.background.type).toBe(ColorType.Solid)
  })

  it("returns transparent background in both themes", () => {
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.background.color).toBe("rgba(0,0,0,0)")
  })

  it("returns light-mode text color in light theme", () => {
    useTheme.setState({ theme: "light" })
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.textColor).toBe("#6b7280")
  })

  it("returns dark-mode text color in dark theme", () => {
    useTheme.setState({ theme: "dark" })
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.textColor).toBe("#9ca3af")
  })

  it("returns light-mode grid color in light theme", () => {
    useTheme.setState({ theme: "light" })
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.gridColor).toBe("rgba(0,0,0,0.06)")
  })

  it("returns dark-mode grid color in dark theme", () => {
    useTheme.setState({ theme: "dark" })
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.gridColor).toBe("rgba(255,255,255,0.06)")
  })

  it("returns light-mode border color in light theme", () => {
    useTheme.setState({ theme: "light" })
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.borderColor).toBe("rgba(0,0,0,0.1)")
  })

  it("returns dark-mode border color in dark theme", () => {
    useTheme.setState({ theme: "dark" })
    const { result } = renderHook(() => useLightweightChartTheme())
    expect(result.current.borderColor).toBe("rgba(255,255,255,0.1)")
  })
})

describe("useRechartsTheme", () => {
  it("returns light-mode tick color in light theme", () => {
    useTheme.setState({ theme: "light" })
    const { result } = renderHook(() => useRechartsTheme())
    expect(result.current.tickColor).toBe("#6b7280")
  })

  it("returns dark-mode tick color in dark theme", () => {
    useTheme.setState({ theme: "dark" })
    const { result } = renderHook(() => useRechartsTheme())
    expect(result.current.tickColor).toBe("#9ca3af")
  })

  it("returns light tooltip background in light theme", () => {
    useTheme.setState({ theme: "light" })
    const { result } = renderHook(() => useRechartsTheme())
    expect(result.current.tooltipBg).toBe("#ffffff")
  })

  it("returns dark tooltip background in dark theme", () => {
    useTheme.setState({ theme: "dark" })
    const { result } = renderHook(() => useRechartsTheme())
    expect(result.current.tooltipBg).toBe("#1f2937")
  })

  it("tooltipStyle backgroundColor matches tooltipBg", () => {
    useTheme.setState({ theme: "dark" })
    const { result } = renderHook(() => useRechartsTheme())
    expect(result.current.tooltipStyle.backgroundColor).toBe(
      result.current.tooltipBg,
    )
  })

  it("tooltipStyle color matches tooltipText", () => {
    useTheme.setState({ theme: "light" })
    const { result } = renderHook(() => useRechartsTheme())
    expect(result.current.tooltipStyle.color).toBe(result.current.tooltipText)
  })

  it("theme switch updates colors", () => {
    useTheme.setState({ theme: "light" })
    const { result, rerender } = renderHook(() => useRechartsTheme())
    const lightTickColor = result.current.tickColor

    act(() => {
      useTheme.setState({ theme: "dark" })
    })
    rerender()

    expect(result.current.tickColor).not.toBe(lightTickColor)
  })
})
