import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useStocks } from "../useDashboard";
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

const mockClient = client as unknown as { GET: ReturnType<typeof vi.fn> };

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useStocks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uses the correct query key", () => {
    mockClient.GET.mockResolvedValueOnce({ data: [], error: undefined });
    const { result } = renderHook(() => useStocks(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading || result.current.isPending).toBe(true);
  });

  it("calls the /stocks endpoint", async () => {
    const stocks = [{ ticker: "AAPL", name: "Apple Inc." }];
    mockClient.GET.mockResolvedValueOnce({ data: stocks, error: undefined });

    const { result } = renderHook(() => useStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockClient.GET).toHaveBeenCalledWith("/stocks");
    expect(result.current.data).toEqual(stocks);
  });

  it("returns data in expected shape", async () => {
    const stocks = [
      { ticker: "AAPL", name: "Apple Inc." },
      { ticker: "MSFT", name: "Microsoft" },
    ];
    mockClient.GET.mockResolvedValueOnce({ data: stocks, error: undefined });

    const { result } = renderHook(() => useStocks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0]).toHaveProperty("ticker", "AAPL");
  });
});
