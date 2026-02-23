import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "@/api/client"
import type {
  RadarStock,
  RemovedStock,
  ScanStatusResponse,
  ThesisLog,
  RemovalLog,
  ResonanceResponse,
  ResonanceMap,
  ResonanceHolding,
  RadarEnrichedStock,
  AddStockRequest,
  DeactivateRequest,
  ReactivateRequest,
  UpdateCategoryRequest,
  ReorderRequest,
  AddThesisRequest,
  StockImportItem,
} from "@/api/types/radar"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useRadarStocks() {
  return useQuery<RadarStock[]>({
    queryKey: ["stocks"],
    queryFn: async () => {
      const { data } = await apiClient.get<RadarStock[]>("/stocks")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRadarEnrichedStocks() {
  return useQuery<RadarEnrichedStock[]>({
    queryKey: ["stocks", "enriched"],
    queryFn: async () => {
      const { data } = await apiClient.get<RadarEnrichedStock[]>("/stocks/enriched")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRemovedStocks() {
  return useQuery<RemovedStock[]>({
    queryKey: ["stocks", "removed"],
    queryFn: async () => {
      const { data } = await apiClient.get<RemovedStock[]>("/stocks/removed")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useScanStatus() {
  return useQuery<ScanStatusResponse>({
    queryKey: ["scan", "status"],
    queryFn: async () => {
      const { data } = await apiClient.get<ScanStatusResponse>("/scan/status")
      return data
    },
    staleTime: 0,
    refetchInterval: 10 * 1000,
  })
}

export function useResonance() {
  return useQuery<ResonanceMap>({
    queryKey: ["resonance"],
    queryFn: async () => {
      const { data } = await apiClient.get<ResonanceResponse>("/resonance")
      // Invert guru-centric response into ticker→gurus map for O(1) card lookup
      const acc: ResonanceMap = {}
      for (const entry of data.results) {
        for (const h of entry.holdings) {
          const item: ResonanceHolding & { guru_display_name: string } = {
            ticker: h.ticker,
            action: h.action,
            weight_pct: h.weight_pct,
            guru_display_name: entry.guru_display_name,
          }
          if (!acc[h.ticker]) acc[h.ticker] = [item]
          else acc[h.ticker].push(item)
        }
      }
      return acc
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}

export function useThesisHistory(ticker: string, enabled: boolean) {
  return useQuery<ThesisLog[]>({
    queryKey: ["thesis", ticker],
    queryFn: async () => {
      const { data } = await apiClient.get<ThesisLog[]>(`/ticker/${ticker}/thesis`)
      return data
    },
    enabled,
    staleTime: 0,
  })
}

export function useRemovalHistory(ticker: string, enabled: boolean) {
  return useQuery<RemovalLog[]>({
    queryKey: ["removals", ticker],
    queryFn: async () => {
      const { data } = await apiClient.get<RemovalLog[]>(`/ticker/${ticker}/removals`)
      return data
    },
    enabled,
    staleTime: 0,
  })
}

export interface PricePoint {
  date: string
  close: number
}

export interface MoatMarginPoint {
  date: string
  value: number | null
}

export interface MoatAnalysis {
  ticker: string
  moat: string
  details?: string
  margin_trend?: MoatMarginPoint[]
}

export function usePriceHistory(ticker: string, enabled: boolean) {
  return useQuery<PricePoint[]>({
    queryKey: ["priceHistory", ticker],
    queryFn: async () => {
      const { data } = await apiClient.get<PricePoint[]>(`/ticker/${ticker}/price-history`)
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMoatAnalysis(ticker: string, enabled: boolean) {
  return useQuery<MoatAnalysis>({
    queryKey: ["moat", ticker],
    queryFn: async () => {
      const { data } = await apiClient.get<MoatAnalysis>(`/ticker/${ticker}/moat`)
      return data
    },
    enabled,
    staleTime: 60 * 60 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useAddStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AddStockRequest) => {
      const { data } = await apiClient.post("/ticker", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}

export function useTriggerScan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/scan")
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scan", "status"] })
    },
  })
}

export function useDeactivateStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticker, payload }: { ticker: string; payload: DeactivateRequest }) => {
      const { data } = await apiClient.post(`/ticker/${ticker}/deactivate`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}

export function useReactivateStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticker, payload }: { ticker: string; payload: ReactivateRequest }) => {
      const { data } = await apiClient.post(`/ticker/${ticker}/reactivate`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}

export function useUpdateCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticker, payload }: { ticker: string; payload: UpdateCategoryRequest }) => {
      const { data } = await apiClient.patch(`/ticker/${ticker}/category`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}

export function useReorderStocks() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: ReorderRequest) => {
      const { data } = await apiClient.put("/stocks/reorder", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}

export function useAddThesis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ ticker, payload }: { ticker: string; payload: AddThesisRequest }) => {
      const { data } = await apiClient.post(`/ticker/${ticker}/thesis`, payload)
      return data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
      queryClient.invalidateQueries({ queryKey: ["thesis", variables.ticker] })
    },
  })
}

export function useImportStocks() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (items: StockImportItem[]) => {
      const { data } = await apiClient.post("/stocks/import", items)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}
