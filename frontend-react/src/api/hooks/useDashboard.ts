import { useQuery } from "@tanstack/react-query"
import apiClient from "@/api/client"
import type {
  Stock,
  EnrichedStock,
  RebalanceResponse,
  FearGreedResponse,
  Snapshot,
  TwrResponse,
  GreatMindsResponse,
  LastScanResponse,
  Holding,
  ProfileResponse,
} from "@/api/types/dashboard"

export function useStocks() {
  return useQuery({
    queryKey: ["stocks"],
    queryFn: async () => {
      const { data } = await apiClient.get<Stock[]>("/stocks")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useEnrichedStocks() {
  return useQuery({
    queryKey: ["stocks", "enriched"],
    queryFn: async () => {
      const { data } = await apiClient.get<EnrichedStock[]>("/stocks/enriched")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useLastScan() {
  return useQuery({
    queryKey: ["scan", "last"],
    queryFn: async () => {
      const { data } = await apiClient.get<LastScanResponse>("/scan/last")
      return data
    },
    staleTime: 120 * 1000,
    refetchInterval: 120 * 1000,
  })
}

export function useHoldings() {
  return useQuery({
    queryKey: ["holdings"],
    queryFn: async () => {
      const { data } = await apiClient.get<Holding[]>("/holdings")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useRebalance(displayCurrency: string) {
  return useQuery({
    queryKey: ["rebalance", displayCurrency],
    queryFn: async () => {
      const { data } = await apiClient.get<RebalanceResponse>("/rebalance", {
        params: { display_currency: displayCurrency },
      })
      return data
    },
    staleTime: 60 * 1000,
  })
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data } = await apiClient.get<ProfileResponse>("/profiles")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useFearGreed() {
  return useQuery({
    queryKey: ["market", "fear-greed"],
    queryFn: async () => {
      const { data } = await apiClient.get<FearGreedResponse>("/market/fear-greed")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useSnapshots(days = 730) {
  return useQuery({
    queryKey: ["snapshots", days],
    queryFn: async () => {
      const { data } = await apiClient.get<Snapshot[]>("/snapshots", {
        params: { days },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useTwr() {
  return useQuery({
    queryKey: ["snapshots", "twr"],
    queryFn: async () => {
      const { data } = await apiClient.get<TwrResponse>("/snapshots/twr")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useGreatMinds() {
  return useQuery({
    queryKey: ["resonance", "great-minds"],
    queryFn: async () => {
      const { data } = await apiClient.get<GreatMindsResponse>("/resonance/great-minds")
      return data
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}
