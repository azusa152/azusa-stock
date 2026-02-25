import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { GuruStyleBadge } from "../GuruStyleBadge"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) =>
      opts?.defaultValue ?? key,
  }),
}))

describe("GuruStyleBadge", () => {
  it("renders null when style is null", () => {
    const { container } = render(<GuruStyleBadge style={null} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders null when style is undefined", () => {
    const { container } = render(<GuruStyleBadge style={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it("renders null for an unknown style value", () => {
    const { container } = render(<GuruStyleBadge style="UNKNOWN_STYLE" />)
    expect(container.firstChild).toBeNull()
  })

  it("renders a badge for VALUE style", () => {
    render(<GuruStyleBadge style="VALUE" />)
    const badge = screen.getByText("VALUE")
    expect(badge).toBeInTheDocument()
    expect(badge.tagName.toLowerCase()).toBe("span")
  })

  it("renders a badge for each known style", () => {
    const styles = ["VALUE", "GROWTH", "MACRO", "QUANT", "ACTIVIST", "MULTI_STRATEGY"]
    for (const style of styles) {
      const { container } = render(<GuruStyleBadge style={style} />)
      expect(container.firstChild).not.toBeNull()
    }
  })

  it("applies sm size classes by default", () => {
    render(<GuruStyleBadge style="VALUE" />)
    const badge = screen.getByText("VALUE")
    expect(badge.className).toContain("text-[10px]")
  })

  it("applies md size classes when size='md'", () => {
    render(<GuruStyleBadge style="VALUE" size="md" />)
    const badge = screen.getByText("VALUE")
    expect(badge.className).toContain("text-xs")
  })
})
