import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { AddStockDrawer } from "../AddStockDrawer"

const mutateMock = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useAddStock: () => ({ mutate: mutateMock, isPending: false }),
  useTriggerScan: () => ({ mutate: vi.fn(), isPending: false }),
  useImportStocks: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/api/hooks/useCrypto", () => ({
  useCryptoSearch: () => ({
    data: [{ id: "bitcoin", symbol: "btc", name: "Bitcoin", thumb: "", ticker: "BTC-USD" }],
  }),
}))

describe("AddStockDrawer crypto mode", () => {
  it("shows crypto search mode and validates thesis before submit", () => {
    render(<AddStockDrawer open={true} onClose={() => undefined} isScanning={false} />)

    fireEvent.click(screen.getByText("radar.form.asset_crypto"))
    expect(screen.getByText("radar.form.crypto_search")).toBeInTheDocument()

    fireEvent.click(screen.getByText("Bitcoin (btc) - BTC-USD"))
    fireEvent.click(screen.getAllByText("radar.form.add_button")[0])

    expect(screen.getByText("radar.form.error_no_thesis")).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })
})
