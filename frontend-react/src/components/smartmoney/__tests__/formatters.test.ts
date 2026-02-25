import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { formatValue, formatShares, isStale, SMART_MONEY_STALE_DAYS } from "../formatters"

describe("formatValue", () => {
  it("returns 'N/A' for null", () => {
    expect(formatValue(null)).toBe("N/A")
  })

  it("returns 'N/A' for undefined", () => {
    expect(formatValue(undefined)).toBe("N/A")
  })

  it("formats billions with 2 decimal places", () => {
    expect(formatValue(2_500_000_000)).toBe("$2.50B")
  })

  it("formats millions with 1 decimal place", () => {
    expect(formatValue(1_800_000)).toBe("$1.8M")
  })

  it("formats thousands with 1 decimal place", () => {
    expect(formatValue(45_000)).toBe("$45.0K")
  })

  it("formats small values with no decimals", () => {
    expect(formatValue(999)).toBe("$999")
  })

  it("formats zero as '$0'", () => {
    expect(formatValue(0)).toBe("$0")
  })

  it("formats exactly 1 billion", () => {
    expect(formatValue(1_000_000_000)).toBe("$1.00B")
  })

  it("formats exactly 1 million", () => {
    expect(formatValue(1_000_000)).toBe("$1.0M")
  })

  it("formats exactly 1 thousand", () => {
    expect(formatValue(1_000)).toBe("$1.0K")
  })
})

describe("formatShares", () => {
  it("returns 'N/A' for null", () => {
    expect(formatShares(null)).toBe("N/A")
  })

  it("returns 'N/A' for undefined", () => {
    expect(formatShares(undefined)).toBe("N/A")
  })

  it("formats millions with 2 decimal places", () => {
    expect(formatShares(3_500_000)).toBe("3.50M")
  })

  it("formats thousands with 1 decimal place", () => {
    expect(formatShares(12_500)).toBe("12.5K")
  })

  it("formats small share counts with no decimals", () => {
    expect(formatShares(500)).toBe("500")
  })

  it("formats exactly 1 million shares", () => {
    expect(formatShares(1_000_000)).toBe("1.00M")
  })

  it("formats exactly 1 thousand shares", () => {
    expect(formatShares(1_000)).toBe("1.0K")
  })
})

describe("isStale", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("returns true for null reportDate", () => {
    expect(isStale(null)).toBe(true)
  })

  it("returns true for undefined reportDate", () => {
    expect(isStale(undefined)).toBe(true)
  })

  it("returns false for a recent date (within stale threshold)", () => {
    const now = new Date("2025-06-01T00:00:00Z")
    vi.setSystemTime(now)
    const recentDate = "2025-05-01" // 31 days ago — within 120-day threshold
    expect(isStale(recentDate)).toBe(false)
  })

  it("returns true for an old date (beyond stale threshold)", () => {
    const now = new Date("2025-06-01T00:00:00Z")
    vi.setSystemTime(now)
    const oldDate = "2024-12-31" // ~152 days ago — beyond 120-day threshold
    expect(isStale(oldDate)).toBe(true)
  })

  it("returns false for today", () => {
    const now = new Date("2025-06-01T00:00:00Z")
    vi.setSystemTime(now)
    expect(isStale("2025-06-01")).toBe(false)
  })

  it(`returns true for exactly ${SMART_MONEY_STALE_DAYS + 1} days ago`, () => {
    const now = new Date("2025-06-01T00:00:00Z")
    vi.setSystemTime(now)
    const pastDate = new Date(now)
    pastDate.setDate(pastDate.getDate() - (SMART_MONEY_STALE_DAYS + 1))
    expect(isStale(pastDate.toISOString().slice(0, 10))).toBe(true)
  })
})
