import { useQuery } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  BackfillStatusResponse,
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

export function useBackfillStatus() {
  return useQuery<BackfillStatusResponse>({
    queryKey: ["backtest", "backfill-status"],
    queryFn: async () => {
      const { data, error } = await client.GET("/backtest/backfill-status")
      if (error) throw error
      return data as unknown as BackfillStatusResponse
    },
    staleTime: 3000,
    // Keep polling so the UI can detect the transition from idle -> backfilling
    // without requiring a manual page refresh.
    refetchInterval: 3000,
    refetchOnWindowFocus: false,
  })
}
