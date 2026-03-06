import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { AddHoldingSheet } from "../AddHoldingSheet"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useAddHolding: () => ({ mutate: vi.fn(), isPending: false }),
  useAddCashHolding: () => ({ mutate: vi.fn(), isPending: false }),
  useImportHoldings: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useHoldings: () => ({ data: [] }),
}))

vi.mock("@/api/hooks/useCrypto", () => ({
  useCryptoSearch: () => ({
    data: [{ id: "bitcoin", symbol: "BTC", name: "Bitcoin", thumb: "", ticker: "BTC-USD" }],
  }),
}))

describe("AddHoldingSheet crypto", () => {
  it("shows crypto tab and search field", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddHoldingSheet open onClose={vi.fn()} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "allocation.sidebar.asset_crypto" }))
    expect(screen.getByText("allocation.sidebar.crypto_search")).toBeInTheDocument()
    expect(screen.getByText("Bitcoin (BTC) - BTC-USD")).toBeInTheDocument()
  })
})
