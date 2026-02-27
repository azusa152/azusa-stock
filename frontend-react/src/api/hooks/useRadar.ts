import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
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
      const { data, error } = await client.GET("/stocks")
      if (error) throw error
      return data as unknown as RadarStock[]
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRadarEnrichedStocks() {
  return useQuery<RadarEnrichedStock[]>({
    queryKey: ["stocks", "enriched"],
    queryFn: async () => {
      const { data, error } = await client.GET("/stocks/enriched")
      if (error) throw error
      return data as unknown as RadarEnrichedStock[]
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRemovedStocks() {
  return useQuery<RemovedStock[]>({
    queryKey: ["stocks", "removed"],
    queryFn: async () => {
      const { data, error } = await client.GET("/stocks/removed")
      if (error) throw error
      return data as unknown as RemovedStock[]
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useScanStatus() {
  return useQuery<ScanStatusResponse>({
    queryKey: ["scan", "status"],
    queryFn: async () => {
      const { data, error } = await client.GET("/scan/status")
      if (error) throw error
      return data as unknown as ScanStatusResponse
    },
    staleTime: 0,
    refetchInterval: 60 * 1000,
  })
}

export function useResonance() {
  return useQuery<ResonanceMap>({
    queryKey: ["resonance"],
    queryFn: async () => {
      const { data, error } = await client.GET("/resonance")
      if (error) throw error
      const response = data as unknown as ResonanceResponse
      // Invert guru-centric response into ticker→gurus map for O(1) card lookup
      const acc: ResonanceMap = {}
      for (const entry of response.results) {
        for (const rawH of entry.holdings) {
          const h = rawH as unknown as ResonanceHolding
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
      const { data, error } = await client.GET("/ticker/{ticker}/thesis", {
        params: { path: { ticker } },
      })
      if (error) throw error
      return data as unknown as ThesisLog[]
    },
    enabled,
    staleTime: 0,
  })
}

export function useRemovalHistory(ticker: string, enabled: boolean) {
  return useQuery<RemovalLog[]>({
    queryKey: ["removals", ticker],
    queryFn: async () => {
      const { data, error } = await client.GET("/ticker/{ticker}/removals", {
        params: { path: { ticker } },
      })
      if (error) throw error
      return data as unknown as RemovalLog[]
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
      const { data, error } = await client.GET("/ticker/{ticker}/price-history", {
        params: { path: { ticker } },
      })
      if (error) throw error
      return data as unknown as PricePoint[]
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMoatAnalysis(ticker: string, enabled: boolean) {
  return useQuery<MoatAnalysis>({
    queryKey: ["moat", ticker],
    queryFn: async () => {
      const { data, error } = await client.GET("/ticker/{ticker}/moat", {
        params: { path: { ticker } },
      })
      if (error) throw error
      return data as unknown as MoatAnalysis
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
      const { data, error } = await client.POST("/ticker", { body: payload })
      if (error) throw error
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
      const { data, error } = await client.POST("/scan")
      if (error) throw error
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
      const { data, error } = await client.POST("/ticker/{ticker}/deactivate", {
        params: { path: { ticker } },
        body: payload,
      })
      if (error) throw error
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
      const { data, error } = await client.POST("/ticker/{ticker}/reactivate", {
        params: { path: { ticker } },
        body: payload,
      })
      if (error) throw error
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
      const { data, error } = await client.PATCH("/ticker/{ticker}/category", {
        params: { path: { ticker } },
        body: payload,
      })
      if (error) throw error
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
      const { data, error } = await client.PUT("/stocks/reorder", { body: payload })
      if (error) throw error
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
      const { data, error } = await client.POST("/ticker/{ticker}/thesis", {
        params: { path: { ticker } },
        body: payload,
      })
      if (error) throw error
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
      const { data, error } = await client.POST("/stocks/import", { body: items })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks"] })
    },
  })
}
