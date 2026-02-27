import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useRadarStocks, useAddStock } from "../useRadar";
import client from "@/api/client";

vi.mock("@/api/client", () => ({
  default: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
    use: vi.fn(),
  },
}));

const mockClient = client as unknown as {
  GET: ReturnType<typeof vi.fn>;
  POST: ReturnType<typeof vi.fn>;
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
    mockClient.GET.mockResolvedValueOnce({ data: [], error: undefined });
    const { result } = renderHook(() => useRadarStocks(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading || result.current.isPending).toBe(true);
  });

  it("calls the /stocks endpoint", async () => {
    const stocks = [{ ticker: "NVDA", name: "NVIDIA" }];
    mockClient.GET.mockResolvedValueOnce({ data: stocks, error: undefined });

    const { result } = renderHook(() => useRadarStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockClient.GET).toHaveBeenCalledWith("/stocks");
    expect(result.current.data).toEqual(stocks);
  });

  it("returns an array of stocks", async () => {
    const stocks = [
      { ticker: "NVDA", name: "NVIDIA" },
      { ticker: "MSFT", name: "Microsoft" },
    ];
    mockClient.GET.mockResolvedValueOnce({ data: stocks, error: undefined });

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
    mockClient.POST.mockResolvedValueOnce({ data: { success: true }, error: undefined });

    const { result } = renderHook(() => useAddStock(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate(payload as Parameters<typeof result.current.mutate>[0]);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockClient.POST).toHaveBeenCalledWith("/ticker", { body: payload });
  });

  it("transitions to success after a resolved mutation", async () => {
    mockClient.POST.mockResolvedValueOnce({ data: { success: true }, error: undefined });

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
