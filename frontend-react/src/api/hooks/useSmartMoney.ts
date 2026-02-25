import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "@/api/client"
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
} from "@/api/types/smartMoney"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useGurus() {
  return useQuery<Guru[]>({
    queryKey: ["gurus"],
    queryFn: async () => {
      const { data } = await apiClient.get<Guru[]>("/gurus")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useGuruDashboard() {
  return useQuery<DashboardResponse>({
    queryKey: ["guruDashboard"],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardResponse>("/gurus/dashboard")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useGuruFiling(id: number, enabled = true) {
  return useQuery<GuruFiling>({
    queryKey: ["guruFiling", id],
    queryFn: async () => {
      const { data } = await apiClient.get<GuruFiling>(`/gurus/${id}/filing`)
      return data
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGuruFilings(id: number, enabled = true) {
  return useQuery<FilingHistoryResponse>({
    queryKey: ["guruFilings", id],
    queryFn: async () => {
      const { data } = await apiClient.get<FilingHistoryResponse>(`/gurus/${id}/filings`)
      return data
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGuruHoldingChanges(id: number, enabled = true) {
  return useQuery<GuruHolding[]>({
    queryKey: ["guruHoldingChanges", id],
    queryFn: async () => {
      const { data } = await apiClient.get<GuruHolding[]>(`/gurus/${id}/holdings?limit=20`)
      return data
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGuruTopHoldings(id: number, enabled = true) {
  return useQuery<GuruHolding[]>({
    queryKey: ["guruTopHoldings", id],
    queryFn: async () => {
      const { data } = await apiClient.get<GuruHolding[]>(`/gurus/${id}/top?n=15`)
      return data
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGreatMinds() {
  return useQuery<GreatMindsResponse>({
    queryKey: ["greatMinds"],
    queryFn: async () => {
      const { data } = await apiClient.get<GreatMindsResponse>("/resonance/great-minds")
      return data
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}

export function useGuruQoQ(id: number, enabled = true) {
  return useQuery<QoQResponse>({
    queryKey: ["guruQoQ", id],
    queryFn: async () => {
      const { data } = await apiClient.get<QoQResponse>(`/gurus/${id}/qoq`)
      return data
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useGrandPortfolio() {
  return useQuery<GrandPortfolioResponse>({
    queryKey: ["grandPortfolio"],
    queryFn: () =>
      apiClient
        .get<GrandPortfolioResponse>("/gurus/grand-portfolio")
        .then((r) => r.data),
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
      const { data } = await apiClient.post<Guru>("/gurus", payload)
      return data
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
      const { data } = await apiClient.post(`/gurus/${id}/sync`)
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
      const { data } = await apiClient.post("/gurus/sync")
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
      await apiClient.delete(`/gurus/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gurus"] })
      queryClient.invalidateQueries({ queryKey: ["guruDashboard"] })
    },
  })
}
