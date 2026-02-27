import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  Guru,
  DashboardResponse,
  GrandPortfolioResponse,
  GuruFiling,
  GuruHolding,
  FilingHistoryResponse,
  GreatMindsResponse,
  QoQResponse,
  AddGuruRequest,
  GuruStyle,
} from "@/api/types/smartMoney"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useGurus() {
  return useQuery<Guru[]>({
    queryKey: ["gurus"],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus")
      if (error) throw error
      return data as unknown as Guru[]
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useGuruDashboard(style?: string | null) {
  return useQuery<DashboardResponse>({
    queryKey: ["guruDashboard", style ?? "all"],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/dashboard", {
        params: { query: style ? { style: style as GuruStyle } : undefined },
      })
      if (error) throw error
      return data as unknown as DashboardResponse
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useGuruFiling(id: number, enabled = true) {
  return useQuery<GuruFiling>({
    queryKey: ["guruFiling", id],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/{guru_id}/filing", {
        params: { path: { guru_id: id } },
      })
      if (error) throw error
      return data as unknown as GuruFiling
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGuruFilings(id: number, enabled = true) {
  return useQuery<FilingHistoryResponse>({
    queryKey: ["guruFilings", id],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/{guru_id}/filings", {
        params: { path: { guru_id: id } },
      })
      if (error) throw error
      return data as unknown as FilingHistoryResponse
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGuruHoldingChanges(id: number, enabled = true, includePerformance = true) {
  return useQuery<GuruHolding[]>({
    queryKey: ["guruHoldingChanges", id, includePerformance],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/{guru_id}/holdings", {
        params: { path: { guru_id: id }, query: { limit: 20, include_performance: includePerformance } },
      })
      if (error) throw error
      return data as unknown as GuruHolding[]
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGuruTopHoldings(id: number, enabled = true, includePerformance = true) {
  return useQuery<GuruHolding[]>({
    queryKey: ["guruTopHoldings", id, includePerformance],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/{guru_id}/top", {
        params: { path: { guru_id: id }, query: { n: 15, include_performance: includePerformance } },
      })
      if (error) throw error
      return data as unknown as GuruHolding[]
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGreatMinds() {
  return useQuery<GreatMindsResponse>({
    queryKey: ["greatMinds"],
    queryFn: async () => {
      const { data, error } = await client.GET("/resonance/great-minds")
      if (error) throw error
      return data as unknown as GreatMindsResponse
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}

export function useGuruQoQ(id: number, enabled = true) {
  return useQuery<QoQResponse>({
    queryKey: ["guruQoQ", id],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/{guru_id}/qoq", {
        params: { path: { guru_id: id } },
      })
      if (error) throw error
      return data as unknown as QoQResponse
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGrandPortfolio(style?: string | null) {
  return useQuery<GrandPortfolioResponse>({
    queryKey: ["grandPortfolio", style ?? "all"],
    queryFn: async () => {
      const { data, error } = await client.GET("/gurus/grand-portfolio", {
        params: { query: style ? { style: style as GuruStyle } : undefined },
      })
      if (error) throw error
      return data as unknown as GrandPortfolioResponse
    },
    staleTime: 5 * 60 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useAddGuru() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AddGuruRequest) => {
      const { data, error } = await client.POST("/gurus", { body: payload })
      if (error) throw error
      return data as unknown as Guru
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gurus"] })
      queryClient.invalidateQueries({ queryKey: ["guruDashboard"] })
    },
  })
}

export function useSyncGuru() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await client.POST("/gurus/{guru_id}/sync", {
        params: { path: { guru_id: id } },
      })
      if (error) throw error
      return data
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["guruFiling", id] })
      queryClient.invalidateQueries({ queryKey: ["guruFilings", id] })
      queryClient.invalidateQueries({ queryKey: ["guruHoldingChanges", id] })
      queryClient.invalidateQueries({ queryKey: ["guruTopHoldings", id] })
      queryClient.invalidateQueries({ queryKey: ["guruDashboard"] })
      queryClient.invalidateQueries({ queryKey: ["gurus"] })
    },
  })
}

export function useSyncAllGurus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/gurus/sync")
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gurus"] })
      queryClient.invalidateQueries({ queryKey: ["guruDashboard"] })
    },
  })
}

export function useDeactivateGuru() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await client.DELETE("/gurus/{guru_id}", {
        params: { path: { guru_id: id } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gurus"] })
      queryClient.invalidateQueries({ queryKey: ["guruDashboard"] })
    },
  })
}
