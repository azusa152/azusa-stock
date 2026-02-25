import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { formatPrice, isMarketOpen } from "../format"

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

describe("isMarketOpen", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("returns false for an unknown market key", () => {
    vi.setSystemTime(new Date("2025-02-25T14:00:00Z")) // Tuesday UTC
    expect(isMarketOpen("UNKNOWN")).toBe(false)
  })

  it("returns false on a Saturday (US market)", () => {
    // 2025-02-22 is a Saturday; 15:00 UTC = 10:00 EST (would be inside US hours on a weekday)
    vi.setSystemTime(new Date("2025-02-22T15:00:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns false on a Sunday (US market)", () => {
    // 2025-02-23 is a Sunday
    vi.setSystemTime(new Date("2025-02-23T15:00:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns false before US market opens (09:29 EST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 14:29 UTC = 09:29 EST
    vi.setSystemTime(new Date("2025-02-25T14:29:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns true during US market hours (10:00 EST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 15:00 UTC = 10:00 EST
    vi.setSystemTime(new Date("2025-02-25T15:00:00Z"))
    expect(isMarketOpen("US")).toBe(true)
  })

  it("returns false after US market closes (16:01 EST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 21:01 UTC = 16:01 EST
    vi.setSystemTime(new Date("2025-02-25T21:01:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns false during JP lunch break (12:00 JST on a Tuesday)", () => {
    // JP lunch: 11:30–12:30 JST. 2025-02-25 (Tuesday) 03:00 UTC = 12:00 JST
    vi.setSystemTime(new Date("2025-02-25T03:00:00Z"))
    expect(isMarketOpen("JP")).toBe(false)
  })

  it("returns true during JP morning session (10:00 JST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 01:00 UTC = 10:00 JST
    vi.setSystemTime(new Date("2025-02-25T01:00:00Z"))
    expect(isMarketOpen("JP")).toBe(true)
  })

  it("returns true during JP afternoon session (13:00 JST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 04:00 UTC = 13:00 JST
    vi.setSystemTime(new Date("2025-02-25T04:00:00Z"))
    expect(isMarketOpen("JP")).toBe(true)
  })

  it("returns false during HK lunch break (12:30 HKT on a Tuesday)", () => {
    // HK lunch: 12:00–13:00 HKT. 2025-02-25 (Tuesday) 04:30 UTC = 12:30 HKT
    vi.setSystemTime(new Date("2025-02-25T04:30:00Z"))
    expect(isMarketOpen("HK")).toBe(false)
  })

  it("returns true during HK afternoon session (14:00 HKT on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 06:00 UTC = 14:00 HKT
    vi.setSystemTime(new Date("2025-02-25T06:00:00Z"))
    expect(isMarketOpen("HK")).toBe(true)
  })

  it("returns true during TW market hours (10:00 CST on a Tuesday)", () => {
    // TW: 09:00–13:30 CST. 2025-02-25 (Tuesday) 02:00 UTC = 10:00 CST
    vi.setSystemTime(new Date("2025-02-25T02:00:00Z"))
    expect(isMarketOpen("TW")).toBe(true)
  })

  it("returns false after TW market closes (13:31 CST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 05:31 UTC = 13:31 CST
    vi.setSystemTime(new Date("2025-02-25T05:31:00Z"))
    expect(isMarketOpen("TW")).toBe(false)
  })
})
