import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "@/api/client"
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
      const { data } = await apiClient.get<FxWatch[]>("/fx-watch")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useFxHistory(base: string, quote: string, enabled = true) {
  return useQuery<FxHistoryPoint[]>({
    queryKey: ["fxHistory", base, quote],
    queryFn: async () => {
      const { data } = await apiClient.get<FxHistoryPoint[]>(`/forex/${base}/${quote}/history-long`)
      return data
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreateFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateFxWatchRequest) => {
      const { data } = await apiClient.post<FxWatch>("/fx-watch", payload)
      return data
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
      const { data } = await apiClient.patch<FxWatch>(`/fx-watch/${id}`, payload)
      return data
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
      await apiClient.delete(`/fx-watch/${id}`)
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
      const { data } = await apiClient.patch<FxWatch>(`/fx-watch/${id}`, { is_active: !isActive })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useCheckFxWatches() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (): Promise<FxAnalysisMap> => {
      const { data } = await apiClient.post<FxCheckResponse>("/fx-watch/check")
      const map: FxAnalysisMap = {}
      for (const r of data.results) {
        const entry: FxAnalysis = {
          current_rate: r.result.current_rate,
          should_alert: r.result.should_alert,
          recommendation: r.result.recommendation_zh,
          reasoning: r.result.reasoning_zh,
        }
        map[r.watch_id] = entry
      }
      return map
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useAlertFxWatches() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/fx-watch/alert")
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}
