import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { GlossaryTerm } from "../GlossaryTerm"

const MOCK_GLOSSARY: Record<string, string> = {
  "glossary.rsi": "RSI measures overbought or oversold conditions.",
  "glossary.bias": "Bias shows distance from moving average.",
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => MOCK_GLOSSARY[key] ?? key,
  }),
}))

describe("GlossaryTerm", () => {
  it("renders children text", () => {
    render(<GlossaryTerm termKey="rsi">RSI</GlossaryTerm>)
    expect(screen.getByText("RSI")).toBeInTheDocument()
  })

  it("renders a button trigger when definition exists", () => {
    render(<GlossaryTerm termKey="rsi">RSI</GlossaryTerm>)
    const trigger = screen.getByRole("button", { name: MOCK_GLOSSARY["glossary.rsi"] })
    expect(trigger).toBeInTheDocument()
    expect(trigger).toHaveClass("underline")
  })

  it("sets aria-label with the glossary definition", () => {
    render(<GlossaryTerm termKey="bias">Bias</GlossaryTerm>)
    const trigger = screen.getByRole("button")
    expect(trigger).toHaveAttribute("aria-label", MOCK_GLOSSARY["glossary.bias"])
  })

  it("renders plain span (no button or tooltip) when key is missing", () => {
    render(<GlossaryTerm termKey="nonexistent">Unknown</GlossaryTerm>)
    expect(screen.getByText("Unknown")).toBeInTheDocument()
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })

  it("fallback span has no aria-label", () => {
    render(<GlossaryTerm termKey="nonexistent">Unknown</GlossaryTerm>)
    const span = screen.getByText("Unknown")
    expect(span).not.toHaveAttribute("aria-label")
  })

  it("applies custom className to the trigger button", () => {
    render(
      <GlossaryTerm termKey="rsi" className="custom-class">
        RSI
      </GlossaryTerm>,
    )
    const trigger = screen.getByRole("button")
    expect(trigger).toHaveClass("custom-class")
  })

  it("applies custom className to fallback span when key is missing", () => {
    render(
      <GlossaryTerm termKey="nonexistent" className="custom-fallback">
        Unknown
      </GlossaryTerm>,
    )
    const span = screen.getByText("Unknown")
    expect(span.tagName).toBe("SPAN")
    expect(span).toHaveClass("custom-fallback")
  })
})
