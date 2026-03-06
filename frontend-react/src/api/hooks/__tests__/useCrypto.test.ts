import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createElement } from "react"
import client from "@/api/client"
import { useCryptoSearch } from "../useCrypto"

vi.mock("@/api/client", () => ({
  default: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
    use: vi.fn(),
  },
}))

const mockClient = client as unknown as { GET: ReturnType<typeof vi.fn> }

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe("useCryptoSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls /crypto/search with q query", async () => {
    mockClient.GET.mockResolvedValueOnce({
      data: [{ id: "bitcoin", symbol: "BTC", name: "Bitcoin", thumb: "", ticker: "BTC-USD" }],
      error: undefined,
    })

    const { result } = renderHook(() => useCryptoSearch("bitcoin"), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockClient.GET).toHaveBeenCalledWith("/crypto/search", {
      params: { query: { q: "bitcoin" } },
    })
  })
})
