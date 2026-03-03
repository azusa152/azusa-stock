import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, act } from "@testing-library/react"

const { mockChangeLanguage, mockApiPut, mockLanguage } = vi.hoisted(() => ({
  mockChangeLanguage: vi.fn().mockResolvedValue(undefined),
  mockApiPut: vi.fn().mockResolvedValue({}),
  mockLanguage: { current: "zh-TW" },
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    i18n: {
      get language() {
        return mockLanguage.current
      },
      changeLanguage: mockChangeLanguage,
    },
  }),
}))

vi.mock("@/api/client", () => ({
  default: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: mockApiPut,
    PATCH: vi.fn(),
    DELETE: vi.fn(),
    use: vi.fn(),
  },
}))

vi.mock("@/hooks/usePrivacyMode", () => ({
  usePrivacyMode: {
    getState: () => ({ isPrivate: false }),
  },
}))

import { useLanguage } from "../useLanguage"

describe("useLanguage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLanguage.current = "zh-TW"
  })

  it("exposes LANGUAGE_OPTIONS with all 4 supported locales", () => {
    const { result } = renderHook(() => useLanguage())
    expect(Object.keys(result.current.LANGUAGE_OPTIONS)).toEqual([
      "zh-TW",
      "en",
      "ja",
      "zh-CN",
    ])
  })

  it("returns the current language from i18n", () => {
    const { result } = renderHook(() => useLanguage())
    expect(result.current.language).toBe("zh-TW")
  })

  it("calls i18n.changeLanguage when changeLanguage is invoked", async () => {
    const { result } = renderHook(() => useLanguage())
    await act(async () => {
      await result.current.changeLanguage("en")
    })
    expect(mockChangeLanguage).toHaveBeenCalledWith("en")
  })

  it("calls the API PUT /settings/preferences after changing language", async () => {
    const { result } = renderHook(() => useLanguage())
    await act(async () => {
      await result.current.changeLanguage("ja")
    })
    expect(mockApiPut).toHaveBeenCalledWith("/settings/preferences", {
      body: {
        language: "ja",
        privacy_mode: false,
      },
    })
  })

  it("does not throw when the API call fails (fail-silent)", async () => {
    mockApiPut.mockRejectedValueOnce(new Error("network error"))
    const { result } = renderHook(() => useLanguage())
    await expect(
      act(async () => {
        await result.current.changeLanguage("en")
      }),
    ).resolves.not.toThrow()
    expect(mockChangeLanguage).toHaveBeenCalledWith("en")
  })
})
