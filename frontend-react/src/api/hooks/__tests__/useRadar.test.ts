import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useRadarStocks, useAddStock } from "../useRadar";
import apiClient from "@/api/client";

vi.mock("@/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() } },
  },
}));

const mockApiClient = apiClient as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useRadarStocks", () => {
  it("is in loading state initially", () => {
    mockApiClient.get.mockResolvedValueOnce({ data: [] });
    const { result } = renderHook(() => useRadarStocks(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading || result.current.isPending).toBe(true);
  });

  it("calls the /stocks endpoint", async () => {
    const stocks = [{ ticker: "NVDA", name: "NVIDIA" }];
    mockApiClient.get.mockResolvedValueOnce({ data: stocks });

    const { result } = renderHook(() => useRadarStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiClient.get).toHaveBeenCalledWith("/stocks");
    expect(result.current.data).toEqual(stocks);
  });

  it("returns an array of stocks", async () => {
    const stocks = [
      { ticker: "NVDA", name: "NVIDIA" },
      { ticker: "MSFT", name: "Microsoft" },
    ];
    mockApiClient.get.mockResolvedValueOnce({ data: stocks });

    const { result } = renderHook(() => useRadarStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data).toHaveLength(2);
  });
});

describe("useAddStock", () => {
  it("posts to /ticker with the provided payload", async () => {
    const payload = { ticker: "AAPL", category: "Moat" };
    mockApiClient.post.mockResolvedValueOnce({ data: { success: true } });

    const { result } = renderHook(() => useAddStock(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate(payload as Parameters<typeof result.current.mutate>[0]);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiClient.post).toHaveBeenCalledWith("/ticker", payload);
  });

  it("transitions to success after a resolved mutation", async () => {
    mockApiClient.post.mockResolvedValueOnce({ data: { success: true } });

    const { result } = renderHook(() => useAddStock(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isIdle).toBe(true);

    await act(async () => {
      result.current.mutate({ ticker: "GOOG" } as Parameters<typeof result.current.mutate>[0]);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
