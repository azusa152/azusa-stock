import { describe, expect, it, vi } from "vitest"
import { render } from "@testing-library/react"
import type { RadarFundamentals } from "@/api/types/radar"
import { FundamentalsSheet } from "../FundamentalsSheet"

const mockUseFundamentals = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useFundamentals: (...args: unknown[]) => mockUseFundamentals(...args),
}))

describe("FundamentalsSheet", () => {
  it("disables fetch when meaningful initial data exists", () => {
    mockUseFundamentals.mockReturnValue({ data: undefined, isLoading: false })

    render(
      <FundamentalsSheet
        ticker="NVDA"
        open
        onOpenChange={() => {}}
        initialData={{ trailing_pe: 20.5 }}
      />,
    )

    expect(mockUseFundamentals).toHaveBeenCalledWith("NVDA", false)
  })

  it("enables fetch when initial data has no usable metrics", () => {
    mockUseFundamentals.mockReturnValue({ data: undefined, isLoading: false })

    render(
      <FundamentalsSheet
        ticker="NVDA"
        open
        onOpenChange={() => {}}
        initialData={{ ticker: "NVDA" } as RadarFundamentals}
      />,
    )

    expect(mockUseFundamentals).toHaveBeenCalledWith("NVDA", true)
  })
})
