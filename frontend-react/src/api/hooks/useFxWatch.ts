import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  FxWatch,
  FxAnalysis,
  FxAnalysisMap,
  FxCheckResponse,
  FxHistoryPoint,
  CreateFxWatchRequest,
  UpdateFxWatchRequest,
} from "@/api/types/fxWatch"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useFxWatches() {
  return useQuery<FxWatch[]>({
    queryKey: ["fxWatches"],
    queryFn: async () => {
      const { data, error } = await client.GET("/fx-watch")
      if (error) throw error
      return data as unknown as FxWatch[]
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useFxHistory(base: string, quote: string, enabled = true) {
  return useQuery<FxHistoryPoint[]>({
    queryKey: ["fxHistory", base, quote],
    queryFn: async () => {
      const { data, error } = await client.GET("/forex/{base}/{quote}/history-long", {
        params: { path: { base, quote } },
      })
      if (error) throw error
      return data as unknown as FxHistoryPoint[]
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

/** Eagerly fetches history for a list of currency pairs for sparklines. */
export function useFxHistoryMap(pairs: Array<{ base: string; quote: string }>) {
  return useQuery<Record<string, FxHistoryPoint[]>>({
    queryKey: ["fxHistoryMap", pairs.map((p) => `${p.base}/${p.quote}`).join(",")],
    queryFn: async () => {
      const entries = await Promise.all(
        pairs.map(async ({ base, quote }) => {
          try {
            const { data, error } = await client.GET("/forex/{base}/{quote}/history-long", {
              params: { path: { base, quote } },
            })
            if (error) return [`${base}/${quote}`, []] as const
            return [`${base}/${quote}`, data as unknown as FxHistoryPoint[]] as const
          } catch {
            return [`${base}/${quote}`, []] as const
          }
        }),
      )
      return Object.fromEntries(entries)
    },
    staleTime: 5 * 60 * 1000,
    enabled: pairs.length > 0,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreateFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateFxWatchRequest) => {
      const { data, error } = await client.POST("/fx-watch", { body: payload })
      if (error) throw error
      return data as unknown as FxWatch
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useUpdateFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateFxWatchRequest }) => {
      const { data, error } = await client.PATCH("/fx-watch/{watch_id}", {
        params: { path: { watch_id: id } },
        body: payload,
      })
      if (error) throw error
      return data as unknown as FxWatch
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useDeleteFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await client.DELETE("/fx-watch/{watch_id}", {
        params: { path: { watch_id: id } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useToggleFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, isActive }: { id: number; isActive: boolean }) => {
      const { data, error } = await client.PATCH("/fx-watch/{watch_id}", {
        params: { path: { watch_id: id } },
        body: { is_active: !isActive },
      })
      if (error) throw error
      return data as unknown as FxWatch
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

async function fetchFxAnalysis(): Promise<FxAnalysisMap> {
  const { data, error } = await client.POST("/fx-watch/check")
  if (error) throw error
  const response = data as unknown as FxCheckResponse
  const map: FxAnalysisMap = {}
  for (const r of response.results) {
    const entry: FxAnalysis = {
      current_rate: r.result.current_rate,
      should_alert: r.result.should_alert,
      recommendation: r.result.recommendation,
      reasoning: r.result.reasoning,
      is_recent_high: r.result.is_recent_high,
      lookback_high: r.result.lookback_high,
      lookback_days: r.result.lookback_days,
      consecutive_increases: r.result.consecutive_increases,
      consecutive_threshold: r.result.consecutive_threshold,
    }
    map[r.watch_id] = entry
  }
  return map
}

/** Auto-fetches analysis for all active FX watches. Enabled only when watches exist. */
export function useFxAnalysis(hasWatches: boolean) {
  return useQuery<FxAnalysisMap>({
    queryKey: ["fxAnalysis"],
    queryFn: fetchFxAnalysis,
    enabled: hasWatches,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}

export function useCheckFxWatches() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fetchFxAnalysis,
    onSuccess: (data) => {
      queryClient.setQueryData(["fxAnalysis"], data)
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useAlertFxWatches() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/fx-watch/alert")
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}
