import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Backtest from "../Backtest"

const mockUseBacktestSummary = vi.fn()
const mockUseBackfillStatus = vi.fn()
const mockUseBacktestDetail = vi.fn()
const toastErrorMock = vi.fn()

const translationMap: Record<string, string> = {
  "config.signal.overheated": "Localized Overheated",
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: { days?: number }) => {
      if (key === "backtest.window_option" && typeof options?.days === "number") {
        return `${options.days}d`
      }
      return translationMap[key] ?? key
    },
  }),
}))

vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => toastErrorMock(...args),
  },
}))

vi.mock("@/api/hooks/useBacktest", () => ({
  useBacktestSummary: () => mockUseBacktestSummary(),
  useBackfillStatus: () => mockUseBackfillStatus(),
  useBacktestDetail: () => mockUseBacktestDetail(),
}))

vi.mock("@/hooks/useRechartsTheme", () => ({
  useRechartsTheme: () => ({
    tickColor: "#666",
    gridColor: "#eee",
    tooltipStyle: {},
  }),
}))

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => <div />,
  Cell: () => <div />,
  Tooltip: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
}))

function renderPage() {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <Backtest />
    </QueryClientProvider>,
  )
}

describe("Backtest export CSV", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})
    mockUseBackfillStatus.mockReturnValue({
      data: { is_backfilling: false, total: 0, completed: 0 },
    })
    mockUseBacktestDetail.mockReturnValue({
      data: { occurrences: [] },
    })
    mockUseBacktestSummary.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        signals: [
          {
            signal: "OVERHEATED",
            direction: "sell",
            confidence: "high",
            windows: [
              { window_days: 5, hit_rate: 0.2, avg_return_pct: 0.5, sample_count: 3 },
              { window_days: 30, hit_rate: 0.5, avg_return_pct: 1.2, sample_count: 2 },
            ],
          },
        ],
        computed_at: "2026-03-04T00:00:00Z",
      },
    })
  })

  it("calls the CSV export API with /api prefix", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["a,b\n1,2"], { type: "text/csv" }),
    })
    vi.stubGlobal("fetch", fetchMock)
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob://test"),
      revokeObjectURL: vi.fn(),
    })

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "backtest.export_csv" }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/backtest/export-csv",
        expect.objectContaining({ headers: expect.any(Object) }),
      ),
    )
  })

  it("shows error toast when export fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, statusText: "Not Found" }))

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "backtest.export_csv" }))

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("common.error"))
  })

  it("renders translated signal labels instead of raw signal keys", () => {
    renderPage()

    expect(screen.getAllByText("Localized Overheated").length).toBeGreaterThan(0)
    expect(screen.queryByText("OVERHEATED")).not.toBeInTheDocument()
  })

  it("updates card metrics when forward window selector changes", () => {
    renderPage()

    expect(screen.getByText((text) => text.includes("50.0%"))).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "5d" }))
    expect(screen.getByText((text) => text.includes("20.0%"))).toBeInTheDocument()
  })
})
