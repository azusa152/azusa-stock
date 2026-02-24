import { describe, it, expect, beforeEach } from "vitest";
import { usePrivacyMode, maskMoney } from "../usePrivacyMode";

// Reset Zustand store state before each test for isolation
beforeEach(() => {
  usePrivacyMode.setState({ isPrivate: false });
});

describe("usePrivacyMode", () => {
  it("starts with privacy mode off", () => {
    expect(usePrivacyMode.getState().isPrivate).toBe(false);
  });

  it("toggle turns privacy mode on", () => {
    usePrivacyMode.getState().toggle();
    expect(usePrivacyMode.getState().isPrivate).toBe(true);
  });

  it("toggle turns privacy mode back off on second call", () => {
    usePrivacyMode.getState().toggle();
    usePrivacyMode.getState().toggle();
    expect(usePrivacyMode.getState().isPrivate).toBe(false);
  });
});

describe("maskMoney", () => {
  it("formats money when privacy mode is off", () => {
    usePrivacyMode.setState({ isPrivate: false });
    expect(maskMoney(1234.56)).toBe("$1,234.56");
  });

  it("returns '***' when privacy mode is on", () => {
    usePrivacyMode.setState({ isPrivate: true });
    expect(maskMoney(1234.56)).toBe("***");
  });

  it("formats zero correctly when privacy mode is off", () => {
    usePrivacyMode.setState({ isPrivate: false });
    expect(maskMoney(0)).toBe("$0.00");
  });

  it("formats large numbers with thousands separators", () => {
    usePrivacyMode.setState({ isPrivate: false });
    expect(maskMoney(1000000)).toBe("$1,000,000.00");
  });
});
