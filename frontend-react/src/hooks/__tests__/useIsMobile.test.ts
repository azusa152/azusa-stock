import { describe, it, expect, afterEach, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useIsMobile } from "../use-mobile"

type MatchMediaCallback = (e: MediaQueryListEvent) => void

function mockMatchMedia(matches: boolean) {
  const listeners: MatchMediaCallback[] = []

  const mql: MediaQueryList = {
    matches,
    media: "",
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: (_: string, cb: EventListenerOrEventListenerObject) => {
      listeners.push(cb as MatchMediaCallback)
    },
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
  }

  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn(() => mql),
  })

  return { mql, listeners }
}

describe("useIsMobile", () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("returns false when window.innerWidth is at or above the mobile breakpoint (768px)", () => {
    Object.defineProperty(window, "innerWidth", { writable: true, value: 1024 })
    mockMatchMedia(false)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it("returns true when window.innerWidth is below the mobile breakpoint (768px)", () => {
    Object.defineProperty(window, "innerWidth", { writable: true, value: 375 })
    mockMatchMedia(true)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(true)
  })

  it("returns false at exactly the breakpoint (768px)", () => {
    Object.defineProperty(window, "innerWidth", { writable: true, value: 768 })
    mockMatchMedia(false)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it("updates when the matchMedia change event fires to a narrower width", () => {
    Object.defineProperty(window, "innerWidth", { writable: true, value: 1024 })
    const { listeners } = mockMatchMedia(false)

    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)

    act(() => {
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        value: 375,
      })
      listeners.forEach((cb) => cb({} as MediaQueryListEvent))
    })

    expect(result.current).toBe(true)
  })

  it("registers a matchMedia change listener on mount", () => {
    const addEventListenerSpy = vi.fn()
    Object.defineProperty(window, "innerWidth", { writable: true, value: 1024 })
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn(() => ({
        matches: false,
        addEventListener: addEventListenerSpy,
        removeEventListener: vi.fn(),
      })),
    })

    renderHook(() => useIsMobile())
    expect(addEventListenerSpy).toHaveBeenCalledWith("change", expect.any(Function))
  })
})
