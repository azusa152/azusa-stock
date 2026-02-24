import { describe, it, expect, beforeEach } from "vitest";
import { useTheme } from "../useTheme";

// Reset Zustand store and DOM before each test
beforeEach(() => {
  useTheme.setState({ theme: "light" });
  document.documentElement.classList.remove("dark");
});

describe("useTheme — state", () => {
  it("starts with light theme", () => {
    expect(useTheme.getState().theme).toBe("light");
  });

  it("setTheme changes theme to dark", () => {
    useTheme.getState().setTheme("dark");
    expect(useTheme.getState().theme).toBe("dark");
  });

  it("setTheme changes theme back to light", () => {
    useTheme.getState().setTheme("dark");
    useTheme.getState().setTheme("light");
    expect(useTheme.getState().theme).toBe("light");
  });

  it("toggle switches from light to dark", () => {
    useTheme.getState().toggle();
    expect(useTheme.getState().theme).toBe("dark");
  });

  it("toggle switches from dark back to light", () => {
    useTheme.setState({ theme: "dark" });
    useTheme.getState().toggle();
    expect(useTheme.getState().theme).toBe("light");
  });
});

describe("useTheme — DOM side effects", () => {
  it("setTheme('dark') adds .dark class to documentElement", () => {
    useTheme.getState().setTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("setTheme('light') removes .dark class from documentElement", () => {
    document.documentElement.classList.add("dark");
    useTheme.getState().setTheme("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggle adds .dark class when starting from light", () => {
    useTheme.getState().toggle();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("toggle removes .dark class when starting from dark", () => {
    useTheme.setState({ theme: "dark" });
    document.documentElement.classList.add("dark");
    useTheme.getState().toggle();
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
