import { useQuery } from "@tanstack/react-query"
import client from "@/api/client"

type CryptoSearchItem = {
  id: string
  symbol: string
  name: string
  thumb: string
  ticker: string
}

export function useCryptoSearch(query: string) {
  return useQuery<CryptoSearchItem[]>({
    queryKey: ["crypto", "search", query],
    queryFn: async () => {
      const { data, error } = await client.GET("/crypto/search", {
        params: { query: { q: query } },
      })
      if (error) throw error
      return (data ?? []) as CryptoSearchItem[]
    },
    enabled: query.trim().length >= 2,
    staleTime: 60 * 1000,
  })
}

export function useCryptoPrice(ticker: string, coingeckoId?: string) {
  return useQuery({
    queryKey: ["crypto", "price", ticker, coingeckoId ?? ""],
    queryFn: async () => {
      const { data, error } = await client.GET("/crypto/price/{ticker}", {
        params: {
          path: { ticker },
          query: { coingecko_id: coingeckoId },
        },
      })
      if (error) throw error
      return data
    },
    enabled: ticker.trim().length > 0,
    staleTime: 60 * 1000,
  })
}
