import { useQuery } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  BacktestDetailResponse,
  BacktestSummaryResponse,
} from "@/api/types/backtest"

export function useBacktestSummary() {
  return useQuery<BacktestSummaryResponse>({
    queryKey: ["backtest", "summary"],
    queryFn: async () => {
      const { data, error } = await client.GET("/backtest/summary")
      if (error) throw error
      return data as unknown as BacktestSummaryResponse
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useBacktestDetail(signal: string, limit = 50, enabled = true) {
  return useQuery<BacktestDetailResponse>({
    queryKey: ["backtest", "detail", signal, limit],
    queryFn: async () => {
      const { data, error } = await client.GET("/backtest/signal/{signal}", {
        params: { path: { signal }, query: { limit } },
      })
      if (error) throw error
      return data as unknown as BacktestDetailResponse
    },
    enabled: enabled && !!signal,
    staleTime: 5 * 60 * 1000,
  })
}
