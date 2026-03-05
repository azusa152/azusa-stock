import { fireEvent, render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import { NetWorthHistoryChart } from "../NetWorthHistoryChart"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  AreaChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Area: () => <div />,
  CartesianGrid: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  Tooltip: () => <div />,
}))

describe("NetWorthHistoryChart", () => {
  it("shows empty state when there are not enough points", () => {
    render(
      <NetWorthHistoryChart
        history={[
          {
            snapshot_date: "2026-03-01",
            investment_value: 1000,
            other_assets_value: 200,
            liabilities_value: 100,
            net_worth: 1100,
            display_currency: "USD",
            breakdown: {},
          },
        ]}
        isLoading={false}
        privacyMode={false}
        timeframe={30}
        onTimeframeChange={vi.fn()}
      />,
    )

    expect(screen.getByText("net_worth.history_empty")).toBeInTheDocument()
  })

  it("triggers timeframe change", () => {
    const onTimeframeChange = vi.fn()
    render(
      <NetWorthHistoryChart
        history={[
          {
            snapshot_date: "2026-03-01",
            investment_value: 1000,
            other_assets_value: 200,
            liabilities_value: 100,
            net_worth: 1100,
            display_currency: "USD",
            breakdown: {},
          },
          {
            snapshot_date: "2026-03-02",
            investment_value: 1010,
            other_assets_value: 210,
            liabilities_value: 100,
            net_worth: 1120,
            display_currency: "USD",
            breakdown: {},
          },
        ]}
        isLoading={false}
        privacyMode={false}
        timeframe={30}
        onTimeframeChange={onTimeframeChange}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "net_worth.timeframe.3m" }))
    expect(onTimeframeChange).toHaveBeenCalledWith(90)
  })

  it("renders chart area when 2+ data points exist", () => {
    render(
      <NetWorthHistoryChart
        history={[
          {
            snapshot_date: "2026-03-01",
            investment_value: 1000,
            other_assets_value: 200,
            liabilities_value: 100,
            net_worth: 1100,
            display_currency: "USD",
            breakdown: {},
          },
          {
            snapshot_date: "2026-03-02",
            investment_value: 1010,
            other_assets_value: 210,
            liabilities_value: 100,
            net_worth: 1120,
            display_currency: "USD",
            breakdown: {},
          },
        ]}
        isLoading={false}
        privacyMode={false}
        timeframe={30}
        onTimeframeChange={vi.fn()}
      />,
    )

    expect(screen.queryByText("net_worth.history_empty")).not.toBeInTheDocument()
    expect(screen.getByText("net_worth.history_title")).toBeInTheDocument()
  })

  it("shows active state on current timeframe button", () => {
    render(
      <NetWorthHistoryChart
        history={[]}
        isLoading={false}
        privacyMode={false}
        timeframe={90}
        onTimeframeChange={vi.fn()}
      />,
    )

    const btn3m = screen.getByRole("button", { name: "net_worth.timeframe.3m" })
    expect(btn3m).toHaveAttribute("aria-pressed", "true")

    const btn1m = screen.getByRole("button", { name: "net_worth.timeframe.1m" })
    expect(btn1m).toHaveAttribute("aria-pressed", "false")
  })
})
