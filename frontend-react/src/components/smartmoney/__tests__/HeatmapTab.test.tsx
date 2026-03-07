import React from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { HeatmapTab } from "../HeatmapTab"
import type { HeatmapResponse } from "@/api/types/smartMoney"
import { ACTION_COLORS } from "@/components/smartmoney/formatters"

const mockUseGuruHeatmap = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (key === "smart_money.heatmap.uniform_action_hint") {
        return `${key}:${String(opts?.action ?? "")}`
      }
      return key
    },
  }),
}))

vi.mock("recharts", () => {
  const TreemapLeafContext = React.createContext<Record<string, unknown> | null>(null)

  function ResponsiveContainer({ children }: { children: React.ReactNode }) {
    return <div data-testid="responsive">{children}</div>
  }

  function Treemap({
    data,
    content,
    children,
  }: {
    data?: Array<{ name?: string; children?: Array<Record<string, unknown>> }>
    content?: React.ReactElement
    children?: React.ReactNode
  }) {
    const groups = data ?? []
    const leaves = groups.flatMap((group) => group.children ?? [])
    const firstLeaf = leaves[0] ?? null
    const CellRenderer = content ? (content as unknown as { type?: React.ComponentType<Record<string, unknown>> }).type : null

    return (
      <TreemapLeafContext.Provider value={firstLeaf}>
        <div data-testid="treemap">
          {groups.map((group, idx) => (
            <div key={`${group.name ?? "group"}-${idx}`} data-testid="treemap-group">
              {group.name}
            </div>
          ))}
          {leaves.map((leaf, idx) => (
            <span
              key={`${String(leaf.ticker ?? "ticker")}-${idx}`}
              data-testid="treemap-leaf"
              data-action-color={String(leaf.actionColor ?? "")}
              data-weight={String(leaf.weightPct ?? "")}
            >
              {String(leaf.ticker ?? "")}
            </span>
          ))}
          {CellRenderer && firstLeaf ? (
            <svg data-testid="heat-cell">
              <CellRenderer {...firstLeaf} x={0} y={0} width={100} height={60} />
            </svg>
          ) : null}
          {children}
        </div>
      </TreemapLeafContext.Provider>
    )
  }

  function Tooltip({ content }: { content?: React.ReactElement }) {
    const firstLeaf = React.useContext(TreemapLeafContext)
    if (!content || !firstLeaf) return null
    const tooltipContent = content as React.ReactElement<Record<string, unknown>>
    return (
      <div data-testid="mock-tooltip">
        {React.cloneElement(tooltipContent, {
          active: true,
          payload: [{ payload: firstLeaf }],
        })}
      </div>
    )
  }

  return { ResponsiveContainer, Treemap, Tooltip }
})

vi.mock("@/api/hooks/useSmartMoney", () => ({
  useGuruHeatmap: (...args: unknown[]) => mockUseGuruHeatmap(...args),
}))

function makeHeatmapResponse(overrides: Partial<HeatmapResponse> = {}): HeatmapResponse {
  return {
    items: [],
    sectors: [],
    report_date: "2025-12-31",
    filing_delay_note: "delay note",
    generated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  }
}

describe("HeatmapTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders uniform-action hint in sector view", () => {
    mockUseGuruHeatmap.mockReturnValue({
      data: makeHeatmapResponse({
        items: [
          {
            ticker: "AAPL",
            company_name: "Apple",
            sector: "Technology",
            guru_count: 1,
            gurus: [],
            combined_value: 1000,
            combined_weight_pct: 10,
            dominant_action: "NEW_POSITION",
            action_breakdown: { NEW_POSITION: 1 },
          },
          {
            ticker: "MSFT",
            company_name: "Microsoft",
            sector: "Technology",
            guru_count: 1,
            gurus: [],
            combined_value: 800,
            combined_weight_pct: 8,
            dominant_action: "NEW_POSITION",
            action_breakdown: { NEW_POSITION: 1 },
          },
        ],
      }),
      isLoading: false,
      isError: false,
    })

    render(<HeatmapTab enabled />)
    expect(screen.getByText("smart_money.heatmap.uniform_action_hint:smart_money.action.new_position")).toBeInTheDocument()
  })

  it("uses actionColor data and renders tooltip content", () => {
    mockUseGuruHeatmap.mockReturnValue({
      data: makeHeatmapResponse({
        items: [
          {
            ticker: "NVDA",
            company_name: "NVIDIA",
            sector: "Technology",
            guru_count: 1,
            gurus: [
              {
                guru_id: 1,
                guru_display_name: "Buffett",
                weight_pct: 7.5,
                action: "INCREASED",
                value: 1234,
              },
            ],
            combined_value: 1234,
            combined_weight_pct: 7.5,
            dominant_action: "INCREASED",
            action_breakdown: { INCREASED: 1 },
          },
        ],
      }),
      isLoading: false,
      isError: false,
    })

    render(<HeatmapTab enabled />)
    const leaf = screen.getByTestId("treemap-leaf")
    expect(leaf).toHaveAttribute("data-action-color", ACTION_COLORS.INCREASED)
    expect(screen.getAllByText("NVDA").length).toBeGreaterThan(0)
    expect(screen.getByText("smart_money.heatmap.guru_label: Buffett")).toBeInTheDocument()
    expect(screen.getAllByText("smart_money.action.increased").length).toBeGreaterThan(0)
  })

  it("creates unknown-guru fallback group when gurus list is empty", () => {
    mockUseGuruHeatmap.mockReturnValue({
      data: makeHeatmapResponse({
        items: [
          {
            ticker: "TSLA",
            company_name: "Tesla",
            sector: "Consumer Discretionary",
            guru_count: 0,
            gurus: [],
            combined_value: 999,
            combined_weight_pct: 4.2,
            dominant_action: "UNCHANGED",
            action_breakdown: { UNCHANGED: 1 },
          },
        ],
      }),
      isLoading: false,
      isError: false,
    })

    render(<HeatmapTab enabled />)
    fireEvent.click(screen.getByText("smart_money.heatmap.view_by_guru"))
    expect(screen.getByText("smart_money.heatmap.unknown_guru")).toBeInTheDocument()
    expect(screen.getAllByText("TSLA").length).toBeGreaterThan(0)
  })
})
