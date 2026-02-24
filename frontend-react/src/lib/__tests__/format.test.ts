import { describe, it, expect } from "vitest"
import { formatPrice } from "../format"

describe("formatPrice", () => {
  it("formats JPY as integer with thousands separator", () => {
    expect(formatPrice(1234.56, "JPY")).toBe("1,235")
  })

  it("formats TWD as integer with thousands separator", () => {
    expect(formatPrice(1234.56, "TWD")).toBe("1,235")
  })

  it("formats USD with 2 decimal places", () => {
    expect(formatPrice(1234.5, "USD")).toBe("1,234.50")
  })

  it("formats HKD with 2 decimal places", () => {
    expect(formatPrice(1234.56, "HKD")).toBe("1,234.56")
  })

  it("rounds JPY 0.5 up to 1", () => {
    expect(formatPrice(0.5, "JPY")).toBe("1")
  })

  it("formats large JPY value with thousands separator", () => {
    expect(formatPrice(12345678, "JPY")).toBe("12,345,678")
  })
})
