import { describe, it, expect } from "vitest";
import { cn, parseUtc, formatLocalTime, formatRelativeTime } from "../utils";

describe("cn", () => {
  it("returns a single class unchanged", () => {
    expect(cn("px-4")).toBe("px-4");
  });

  it("merges multiple classes", () => {
    expect(cn("px-4", "py-2")).toBe("px-4 py-2");
  });

  it("deduplicates conflicting Tailwind classes (last wins)", () => {
    expect(cn("px-4", "px-8")).toBe("px-8");
  });

  it("ignores falsy values", () => {
    expect(cn("px-4", false, undefined, null, "py-2")).toBe("px-4 py-2");
  });

  it("handles conditional class objects", () => {
    expect(cn({ "font-bold": true, italic: false })).toBe("font-bold");
  });
});

describe("parseUtc", () => {
  it("appends Z to a naive ISO string so it is treated as UTC", () => {
    const date = parseUtc("2026-02-23T08:36:17");
    expect(date.getUTCFullYear()).toBe(2026);
    expect(date.getUTCMonth()).toBe(1); // 0-indexed
    expect(date.getUTCDate()).toBe(23);
    expect(date.getUTCHours()).toBe(8);
    expect(date.getUTCMinutes()).toBe(36);
    expect(date.getUTCSeconds()).toBe(17);
  });

  it("does not double-append Z when Z is already present", () => {
    const date = parseUtc("2026-02-23T08:36:17Z");
    expect(date.getUTCHours()).toBe(8);
  });

  it("does not modify a string that already has a UTC offset (+)", () => {
    const date = parseUtc("2026-02-23T08:36:17+09:00");
    // 08:36 JST = 23:36 UTC previous day
    expect(date.getUTCHours()).toBe(23);
  });

  it("returns a valid Date for a date-only ISO string", () => {
    const date = parseUtc("2026-01-01");
    expect(date instanceof Date).toBe(true);
    expect(isNaN(date.getTime())).toBe(false);
  });
});

describe("formatLocalTime", () => {
  it("returns a non-empty string for a valid ISO timestamp", () => {
    const result = formatLocalTime("2026-02-23T08:36:17");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("contains the year in the formatted string", () => {
    const result = formatLocalTime("2026-02-23T08:36:17");
    expect(result).toContain("2026");
  });
});

describe("formatRelativeTime", () => {
  it("formats 0 seconds as at least 1 minute ago", () => {
    expect(formatRelativeTime(0, "en")).toBe("1 minute ago");
  });

  it("formats minute/hour/day boundaries correctly", () => {
    expect(formatRelativeTime(59 * 60, "en")).toBe("59 minutes ago");
    expect(formatRelativeTime(60 * 60, "en")).toBe("1 hour ago");
    expect(formatRelativeTime(23 * 60 * 60, "en")).toBe("23 hours ago");
    expect(formatRelativeTime(24 * 60 * 60, "en")).toBe("yesterday");
  });

  it("forwards the locale to Intl.RelativeTimeFormat", () => {
    const ja = formatRelativeTime(60 * 60, "ja");
    expect(ja).toContain("前");
  });

  it("returns an empty string for non-finite values", () => {
    expect(formatRelativeTime(Number.NaN, "en")).toBe("");
    expect(formatRelativeTime(Number.POSITIVE_INFINITY, "en")).toBe("");
  });
});
