import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ActivityFeed } from "../ActivityFeed"
import type { ActivityFeed as ActivityFeedType } from "@/api/types/smartMoney"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key,
  }),
}))

function makeActivityFeed(
  overrides: Partial<ActivityFeedType> = {},
): ActivityFeedType {
  return {
    most_bought: [],
    most_sold: [],
    ...overrides,
  }
}

describe("ActivityFeed", () => {
  it("renders two column headers", () => {
    render(<ActivityFeed data={makeActivityFeed()} />)
    expect(screen.getByText("smart_money.activity.most_bought")).toBeInTheDocument()
    expect(screen.getByText("smart_money.activity.most_sold")).toBeInTheDocument()
  })

  it("shows empty state for both lists when empty", () => {
    render(<ActivityFeed data={makeActivityFeed()} />)
    expect(screen.getByText("smart_money.activity.empty_bought")).toBeInTheDocument()
    expect(screen.getByText("smart_money.activity.empty_sold")).toBeInTheDocument()
  })

  it("renders items in most_bought list", () => {
    const data = makeActivityFeed({
      most_bought: [
        {
          ticker: "AAPL",
          company_name: "Apple Inc",
          guru_count: 3,
          gurus: ["Warren Buffett", "Ray Dalio", "Ken Griffin"],
          total_value: 1_500_000_000,
        },
      ],
    })
    render(<ActivityFeed data={data} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText(/Warren Buffett/)).toBeInTheDocument()
  })

  it("renders items in most_sold list", () => {
    const data = makeActivityFeed({
      most_sold: [
        {
          ticker: "TSLA",
          company_name: "Tesla Inc",
          guru_count: 2,
          gurus: ["George Soros", "David Tepper"],
          total_value: 200_000_000,
        },
      ],
    })
    render(<ActivityFeed data={data} />)
    expect(screen.getByText("TSLA")).toBeInTheDocument()
    expect(screen.getByText(/George Soros/)).toBeInTheDocument()
  })

  it("does not show empty bought message when most_bought has items", () => {
    const data = makeActivityFeed({
      most_bought: [
        {
          ticker: "NVDA",
          company_name: "Nvidia Corp",
          guru_count: 1,
          gurus: ["Ken Griffin"],
          total_value: 500_000_000,
        },
      ],
    })
    render(<ActivityFeed data={data} />)
    expect(
      screen.queryByText("smart_money.activity.empty_bought"),
    ).not.toBeInTheDocument()
  })

  it("renders guru_count label for each item", () => {
    const data = makeActivityFeed({
      most_bought: [
        {
          ticker: "META",
          company_name: "Meta Platforms",
          guru_count: 4,
          gurus: ["Buffett", "Dalio", "Griffin", "Klarman"],
          total_value: 800_000_000,
        },
      ],
    })
    render(<ActivityFeed data={data} />)
    // span contains "{guru_count} {guru_count_label}" as a single text node
    expect(
      screen.getByText(/4.*smart_money\.activity\.guru_count_label/),
    ).toBeInTheDocument()
  })
})
