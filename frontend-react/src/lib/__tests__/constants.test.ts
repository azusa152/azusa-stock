import { describe, it, expect } from "vitest";
import {
  SCAN_SIGNAL_ICONS,
  BUY_OPPORTUNITY_SIGNALS,
  RISK_WARNING_SIGNALS,
  STOCK_CATEGORIES,
  RADAR_CATEGORIES,
  CATEGORY_ICON_SHORT,
  CATEGORY_COLOR_MAP,
} from "../constants";

describe("SCAN_SIGNAL_ICONS", () => {
  const EXPECTED_SIGNALS = [
    "THESIS_BROKEN",
    "DEEP_VALUE",
    "OVERSOLD",
    "CONTRARIAN_BUY",
    "APPROACHING_BUY",
    "OVERHEATED",
    "CAUTION_HIGH",
    "WEAKENING",
    "NORMAL",
  ];

  it("defines exactly 9 signals (matches backend 9-state taxonomy)", () => {
    expect(Object.keys(SCAN_SIGNAL_ICONS)).toHaveLength(9);
  });

  it("contains all expected signal keys", () => {
    for (const signal of EXPECTED_SIGNALS) {
      expect(SCAN_SIGNAL_ICONS).toHaveProperty(signal);
    }
  });

  it("every signal maps to a non-empty icon string", () => {
    for (const icon of Object.values(SCAN_SIGNAL_ICONS)) {
      expect(typeof icon).toBe("string");
      expect(icon.length).toBeGreaterThan(0);
    }
  });
});

describe("BUY_OPPORTUNITY_SIGNALS and RISK_WARNING_SIGNALS", () => {
  it("BUY_OPPORTUNITY_SIGNALS contains expected buy signals", () => {
    expect(BUY_OPPORTUNITY_SIGNALS.has("DEEP_VALUE")).toBe(true);
    expect(BUY_OPPORTUNITY_SIGNALS.has("OVERSOLD")).toBe(true);
    expect(BUY_OPPORTUNITY_SIGNALS.has("CONTRARIAN_BUY")).toBe(true);
    expect(BUY_OPPORTUNITY_SIGNALS.has("APPROACHING_BUY")).toBe(true);
  });

  it("RISK_WARNING_SIGNALS contains expected warning signals", () => {
    expect(RISK_WARNING_SIGNALS.has("THESIS_BROKEN")).toBe(true);
    expect(RISK_WARNING_SIGNALS.has("OVERHEATED")).toBe(true);
    expect(RISK_WARNING_SIGNALS.has("CAUTION_HIGH")).toBe(true);
  });

  it("buy and warning signal sets do not overlap", () => {
    const overlap = [...BUY_OPPORTUNITY_SIGNALS].filter((s) =>
      RISK_WARNING_SIGNALS.has(s)
    );
    expect(overlap).toHaveLength(0);
  });
});

describe("STOCK_CATEGORIES", () => {
  it("includes Trend_Setter as the first category", () => {
    expect(STOCK_CATEGORIES[0]).toBe("Trend_Setter");
  });

  it("includes all 5 expected categories", () => {
    expect(STOCK_CATEGORIES).toContain("Trend_Setter");
    expect(STOCK_CATEGORIES).toContain("Moat");
    expect(STOCK_CATEGORIES).toContain("Growth");
    expect(STOCK_CATEGORIES).toContain("Bond");
    expect(STOCK_CATEGORIES).toContain("Cash");
  });

  it("has 5 categories total", () => {
    expect(STOCK_CATEGORIES).toHaveLength(5);
  });
});

describe("RADAR_CATEGORIES", () => {
  it("excludes Cash (Cash is not a radar category)", () => {
    expect(RADAR_CATEGORIES).not.toContain("Cash");
  });

  it("has 4 categories total", () => {
    expect(RADAR_CATEGORIES).toHaveLength(4);
  });
});

describe("CATEGORY_ICON_SHORT and CATEGORY_COLOR_MAP", () => {
  it("CATEGORY_ICON_SHORT has an entry for every STOCK_CATEGORY", () => {
    for (const cat of STOCK_CATEGORIES) {
      expect(CATEGORY_ICON_SHORT).toHaveProperty(cat);
    }
  });

  it("CATEGORY_COLOR_MAP has an entry for every STOCK_CATEGORY", () => {
    for (const cat of STOCK_CATEGORIES) {
      expect(CATEGORY_COLOR_MAP).toHaveProperty(cat);
    }
  });

  it("every CATEGORY_COLOR_MAP value is a valid hex color", () => {
    for (const color of Object.values(CATEGORY_COLOR_MAP)) {
      expect(color).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });
});
