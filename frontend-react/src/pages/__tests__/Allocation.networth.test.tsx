import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Allocation from "../Allocation"

const mockUseNetWorthSummary = vi.fn()
const mockUseNetWorthItems = vi.fn()
const mockUseNetWorthHistory = vi.fn()
const mockUseNetWorthSeedPreview = vi.fn()
const mockUseSeedNetWorth = vi.fn()
const mockSeedMutate = vi.fn()
const mockUseProfile = vi.fn()
const mockUseHoldings = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { count?: number; value?: string }) => {
      if (key === "net_worth.seed_success" && typeof options?.count === "number") {
        return `seed_success_${options.count}`
      }
      if (
        (key === "net_worth.seed_preview_investment" || key === "net_worth.seed_preview_cash") &&
        typeof options?.value === "string"
      ) {
        return `${key}:${options.value}`
      }
      return key
    },
  }),
}))

vi.mock("react-router-dom", () => ({
  useSearchParams: () => [new URLSearchParams("tab=net-worth")],
}))

vi.mock("@/hooks/usePrivacyMode", () => ({
  usePrivacyMode: () => false,
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useProfile: () => mockUseProfile(),
  useHoldings: () => mockUseHoldings(),
}))

vi.mock("@/api/hooks/useNetWorth", () => ({
  useNetWorthSummary: () => mockUseNetWorthSummary(),
  useNetWorthItems: () => mockUseNetWorthItems(),
  useNetWorthHistory: () => mockUseNetWorthHistory(),
  useNetWorthSeedPreview: () => mockUseNetWorthSeedPreview(),
  useSeedNetWorth: () => mockUseSeedNetWorth(),
}))

vi.mock("@/components/allocation/holdings/AddHoldingSheet", () => ({
  AddHoldingSheet: () => null,
}))
vi.mock("@/components/allocation/networth/AddNetWorthItemSheet", () => ({
  AddNetWorthItemSheet: () => null,
}))
vi.mock("@/components/allocation/analysis/RebalanceAnalysis", () => ({
  RebalanceAnalysis: () => null,
}))
vi.mock("@/components/allocation/tools/CurrencyExposure", () => ({
  CurrencyExposure: () => null,
}))
vi.mock("@/components/allocation/tools/StressTest", () => ({
  StressTest: () => null,
}))
vi.mock("@/components/allocation/tools/SmartWithdrawal", () => ({
  SmartWithdrawal: () => null,
}))
vi.mock("@/components/allocation/tools/TargetAllocation", () => ({
  TargetAllocation: () => null,
}))
vi.mock("@/components/allocation/holdings/HoldingsManager", () => ({
  HoldingsManager: () => null,
}))
vi.mock("@/components/allocation/settings/TelegramSettings", () => ({
  TelegramSettings: () => null,
}))
vi.mock("@/components/allocation/settings/NotificationPreferences", () => ({
  NotificationPreferences: () => null,
}))

describe("Allocation net worth cold start", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseProfile.mockReturnValue({
      data: { user_id: "default" },
      isLoading: false,
    })
    mockUseHoldings.mockReturnValue({
      data: [{ id: 1, ticker: "AAPL" }],
      isLoading: false,
    })
    mockUseNetWorthSummary.mockReturnValue({ data: undefined })
    mockUseNetWorthItems.mockReturnValue({ data: [] })
    mockUseNetWorthHistory.mockReturnValue({ data: [], isLoading: false })
    mockUseNetWorthSeedPreview.mockReturnValue({
      data: {
        has_holdings: true,
        investment_value: 50000,
        cash_value: 10000,
        cash_positions: [{ currency: "USD", amount: 10000 }],
        existing_item_count: 0,
        display_currency: "USD",
      },
    })
    mockUseSeedNetWorth.mockReturnValue({
      isPending: false,
      mutate: mockSeedMutate,
    })
  })

  it("shows seed preview and imports cash positions", async () => {
    mockSeedMutate.mockImplementation((_v: unknown, opts?: { onSuccess?: (result: { created_items: unknown[] }) => void }) => {
      opts?.onSuccess?.({ created_items: [{}] })
    })

    render(<Allocation />)

    expect(screen.getByText("net_worth.seed_preview_title")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "net_worth.seed_import_btn" }))

    await waitFor(() => {
      expect(screen.getByText("seed_success_1")).toBeInTheDocument()
    })
  })
})
