import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  NetWorthItemRequest,
  NetWorthItemResponse,
  NetWorthSeedPreviewResponse,
  NetWorthSeedResponse,
  NetWorthSnapshotResponse,
  NetWorthSummaryResponse,
  UpdateNetWorthItemRequest,
} from "@/api/types/networth"

export function useNetWorthSummary(displayCurrency = "USD", enabled = true) {
  return useQuery<NetWorthSummaryResponse>({
    queryKey: ["net-worth", "summary", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/net-worth", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return data as unknown as NetWorthSummaryResponse
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useNetWorthItems(displayCurrency = "USD", enabled = true) {
  return useQuery<NetWorthItemResponse[]>({
    queryKey: ["net-worth", "items", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/net-worth/items", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return (data ?? []) as unknown as NetWorthItemResponse[]
    },
    staleTime: 30 * 1000,
    enabled,
  })
}

export function useNetWorthHistory(days = 30, displayCurrency = "USD", enabled = true) {
  return useQuery<NetWorthSnapshotResponse[]>({
    queryKey: ["net-worth", "history", days, displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/net-worth/history", {
        params: { query: { days, display_currency: displayCurrency } },
      })
      if (error) throw error
      return (data ?? []) as unknown as NetWorthSnapshotResponse[]
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useNetWorthSeedPreview(displayCurrency = "USD", enabled = true) {
  return useQuery<NetWorthSeedPreviewResponse>({
    queryKey: ["net-worth", "seed-preview", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/net-worth/seed-preview", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return data as unknown as NetWorthSeedPreviewResponse
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useSeedNetWorth() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/net-worth/seed")
      if (error) throw error
      return data as unknown as NetWorthSeedResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["net-worth"] })
    },
  })
}

export function useCreateNetWorthItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: NetWorthItemRequest) => {
      const { data, error } = await client.POST("/net-worth/items", { body: payload })
      if (error) throw error
      return data as unknown as NetWorthItemResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["net-worth"] })
    },
  })
}

export function useUpdateNetWorthItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number
      payload: UpdateNetWorthItemRequest
    }) => {
      const { data, error } = await client.PUT("/net-worth/items/{item_id}", {
        params: { path: { item_id: id } },
        body: payload,
      })
      if (error) throw error
      return data as unknown as NetWorthItemResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["net-worth"] })
    },
  })
}

export function useDeleteNetWorthItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await client.DELETE("/net-worth/items/{item_id}", {
        params: { path: { item_id: id } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["net-worth"] })
    },
  })
}
