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
            interest_rate: null,
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
})
