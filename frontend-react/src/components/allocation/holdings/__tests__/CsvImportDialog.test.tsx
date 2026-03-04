import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { CsvImportDialog } from "../CsvImportDialog"

const mutateMock = vi.fn()
const { parseCSVMock } = vi.hoisted(() => ({ parseCSVMock: vi.fn() }))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { count?: number }) =>
      typeof opts?.count === "number" ? `${key}:${opts.count}` : key,
  }),
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useImportHoldings: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}))

vi.mock("@/lib/csv-import", async () => {
  const actual = await vi.importActual<typeof import("@/lib/csv-import")>("@/lib/csv-import")
  return {
    ...actual,
    parseCSV: parseCSVMock.mockResolvedValue({
      headers: ["Ticker", "Qty", "Category", "Currency"],
      rows: [{ Ticker: "AAPL", Qty: "10", Category: "Growth", Currency: "USD" }],
      warnings: [],
    }),
  }
})

function renderDialog() {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <CsvImportDialog open onClose={vi.fn()} />
    </QueryClientProvider>,
  )
}

describe("CsvImportDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    parseCSVMock.mockResolvedValue({
      headers: ["Ticker", "Qty", "Category", "Currency"],
      rows: [{ Ticker: "AAPL", Qty: "10", Category: "Growth", Currency: "USD" }],
      warnings: [],
    })
  })

  it("renders, accepts CSV file upload, and shows preview step", async () => {
    renderDialog()

    const input = document.querySelector("input[type='file']") as HTMLInputElement
    const file = new File(["Ticker,Qty,Category,Currency\nAAPL,10,Growth,USD"], "holdings.csv", {
      type: "text/csv",
    })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() =>
      expect(screen.getByText("allocation.csv_import.map_columns")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "allocation.csv_import.next" }))
    await waitFor(() =>
      expect(screen.getByText("allocation.csv_import.preview_title")).toBeInTheDocument(),
    )
  })

  it("blocks zero-row import in preview", async () => {
    parseCSVMock.mockResolvedValue({
      headers: ["Ticker", "Qty", "Category", "Currency"],
      rows: [],
      warnings: [],
    })

    renderDialog()
    const input = document.querySelector("input[type='file']") as HTMLInputElement
    const file = new File(["Ticker,Qty,Category,Currency\n"], "holdings.csv", {
      type: "text/csv",
    })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() =>
      expect(screen.getByText("allocation.csv_import.map_columns")).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole("button", { name: "allocation.csv_import.next" }))
    await waitFor(() =>
      expect(screen.getByText("allocation.csv_import.preview_title")).toBeInTheDocument(),
    )

    const importButton = screen.getByRole("button", { name: "allocation.csv_import.confirm_import:0" })
    expect(importButton).toBeDisabled()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it("allows cash-only CSV without ticker mapping and can import", async () => {
    parseCSVMock.mockResolvedValue({
      headers: ["Qty", "Category", "Currency"],
      rows: [{ Qty: "1000", Category: "Cash", Currency: "USD" }],
      warnings: [],
    })

    renderDialog()
    const input = document.querySelector("input[type='file']") as HTMLInputElement
    const file = new File(["Qty,Category,Currency\n1000,Cash,USD\n"], "holdings.csv", {
      type: "text/csv",
    })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() =>
      expect(screen.getByText("allocation.csv_import.map_columns")).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole("button", { name: "allocation.csv_import.next" }))
    await waitFor(() =>
      expect(screen.getByText("allocation.csv_import.preview_title")).toBeInTheDocument(),
    )

    const importButton = screen.getByRole("button", { name: "allocation.csv_import.confirm_import:1" })
    expect(importButton).toBeDisabled()

    fireEvent.click(screen.getByRole("checkbox"))
    await waitFor(() => expect(importButton).not.toBeDisabled())
    fireEvent.click(importButton)

    expect(mutateMock).toHaveBeenCalledTimes(1)
  })
})
