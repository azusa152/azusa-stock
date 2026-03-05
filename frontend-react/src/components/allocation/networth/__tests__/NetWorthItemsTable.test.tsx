import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { NetWorthItemsTable } from "../NetWorthItemsTable"

const updateMutateMock = vi.fn()
const deleteMutateMock = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { days?: number }) =>
      typeof opts?.days === "number" ? `${key}:${opts.days}` : key,
  }),
}))

vi.mock("@/api/hooks/useNetWorth", () => ({
  useUpdateNetWorthItem: () => ({
    mutate: updateMutateMock,
    isPending: false,
  }),
  useDeleteNetWorthItem: () => ({
    mutate: deleteMutateMock,
    isPending: false,
  }),
}))

describe("NetWorthItemsTable", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders empty state when no items", () => {
    render(<NetWorthItemsTable items={[]} privacyMode={false} />)
    expect(screen.getByText("net_worth.empty")).toBeInTheDocument()
  })

  it("calls update mutation when editing value", () => {
    render(
      <NetWorthItemsTable
        items={[
          {
            id: 1,
            name: "Savings",
            kind: "asset",
            category: "savings",
            value: 1000,
            value_display: 1000,
            currency: "USD",
            fx_rate_to_usd: null,
            interest_rate: null,
            minimum_payment: null,
            source: "manual",
            note: "",
            is_active: true,
            is_stale: true,
            days_since_update: 120,
            created_at: "2026-03-01T00:00:00Z",
            updated_at: "2026-03-01T00:00:00Z",
          },
        ]}
        privacyMode={false}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "common.edit" }))
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "1200" } })
    fireEvent.click(screen.getByRole("button", { name: "common.save" }))

    expect(updateMutateMock).toHaveBeenCalledWith(
      { id: 1, payload: { value: 1200 } },
      expect.any(Object),
    )
  })

  it("shows liability section and annual interest hint", () => {
    render(
      <NetWorthItemsTable
        items={[
          {
            id: 2,
            name: "Credit Card",
            kind: "liability",
            category: "credit_card",
            value: 1000,
            value_display: 1000,
            currency: "USD",
            fx_rate_to_usd: null,
            interest_rate: 12,
            minimum_payment: 50,
            source: "manual",
            note: "",
            is_active: true,
            is_stale: false,
            days_since_update: 1,
            created_at: "2026-03-01T00:00:00Z",
            updated_at: "2026-03-01T00:00:00Z",
          },
        ]}
        privacyMode={false}
      />,
    )

    expect(screen.getByText("net_worth.kind.liability")).toBeInTheDocument()
    expect(screen.getByText("net_worth.annual_interest_hint")).toBeInTheDocument()
  })

  it("masks values in privacy mode", () => {
    render(
      <NetWorthItemsTable
        items={[
          {
            id: 1,
            name: "Savings",
            kind: "asset",
            category: "savings",
            value: 5000,
            value_display: 5000,
            currency: "USD",
            fx_rate_to_usd: null,
            interest_rate: null,
            minimum_payment: null,
            source: "manual",
            note: "",
            is_active: true,
            is_stale: false,
            days_since_update: 0,
            created_at: "2026-03-01T00:00:00Z",
            updated_at: "2026-03-01T00:00:00Z",
          },
        ]}
        privacyMode={true}
      />,
    )

    expect(screen.getByText("***")).toBeInTheDocument()
  })

  it("shows stale warning for stale items", () => {
    render(
      <NetWorthItemsTable
        items={[
          {
            id: 1,
            name: "Property",
            kind: "asset",
            category: "property",
            value: 300000,
            value_display: 300000,
            currency: "USD",
            fx_rate_to_usd: null,
            interest_rate: null,
            minimum_payment: null,
            source: "manual",
            note: "",
            is_active: true,
            is_stale: true,
            days_since_update: 95,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ]}
        privacyMode={false}
      />,
    )

    expect(screen.getByText("net_worth.last_updated_days:95")).toBeInTheDocument()
  })

  it("triggers delete flow on confirm", () => {
    render(
      <NetWorthItemsTable
        items={[
          {
            id: 3,
            name: "Car Loan",
            kind: "liability",
            category: "loan",
            value: 8000,
            value_display: 8000,
            currency: "USD",
            fx_rate_to_usd: null,
            interest_rate: 5,
            minimum_payment: 200,
            source: "manual",
            note: "",
            is_active: true,
            is_stale: false,
            days_since_update: 2,
            created_at: "2026-03-01T00:00:00Z",
            updated_at: "2026-03-01T00:00:00Z",
          },
        ]}
        privacyMode={false}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "common.delete" }))
    fireEvent.click(screen.getByRole("button", { name: "common.confirm" }))

    expect(deleteMutateMock).toHaveBeenCalledWith(3, expect.any(Object))
  })
})
