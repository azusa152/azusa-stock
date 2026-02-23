import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "@/api/client"
import type {
  PersonaTemplate,
  AllocRebalanceResponse,
  CurrencyExposureResponse,
  StressTestResponse,
  WithdrawResponse,
  TelegramSettings,
  AllocPreferencesResponse,
  AddHoldingRequest,
  AddCashRequest,
  UpdateHoldingRequest,
  WithdrawRequest,
  CreateProfileRequest,
  UpdateProfileRequest,
  SaveTelegramRequest,
  SavePreferencesRequest,
} from "@/api/types/allocation"
import type { Holding, ProfileResponse } from "@/api/types/allocation"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useTemplates() {
  return useQuery<PersonaTemplate[]>({
    queryKey: ["personas", "templates"],
    queryFn: async () => {
      const { data } = await apiClient.get<PersonaTemplate[]>("/personas/templates")
      return data
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}

export function useAllocRebalance(displayCurrency: string, enabled = true) {
  return useQuery<AllocRebalanceResponse>({
    queryKey: ["rebalance", displayCurrency],
    queryFn: async () => {
      const { data } = await apiClient.get<AllocRebalanceResponse>("/rebalance", {
        params: { display_currency: displayCurrency },
      })
      return data
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useCurrencyExposure(enabled = true) {
  return useQuery<CurrencyExposureResponse>({
    queryKey: ["currency-exposure"],
    queryFn: async () => {
      const { data } = await apiClient.get<CurrencyExposureResponse>("/currency-exposure")
      return data
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useStressTest(dropPct: number, currency: string, enabled = true) {
  return useQuery<StressTestResponse>({
    queryKey: ["stress-test", dropPct, currency],
    queryFn: async () => {
      const { data } = await apiClient.get<StressTestResponse>("/stress-test", {
        params: { scenario_drop_pct: dropPct, display_currency: currency },
      })
      return data
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useTelegramSettings() {
  return useQuery<TelegramSettings>({
    queryKey: ["settings", "telegram"],
    queryFn: async () => {
      const { data } = await apiClient.get<TelegramSettings>("/settings/telegram")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePreferences() {
  return useQuery<AllocPreferencesResponse>({
    queryKey: ["settings", "preferences"],
    queryFn: async () => {
      const { data } = await apiClient.get<AllocPreferencesResponse>("/settings/preferences")
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateProfileRequest) => {
      const { data } = await apiClient.post<ProfileResponse>("/profiles", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] })
    },
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateProfileRequest }) => {
      const { data } = await apiClient.put<ProfileResponse>(`/profiles/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] })
      queryClient.invalidateQueries({ queryKey: ["currency-exposure"] })
    },
  })
}

export function useAddHolding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AddHoldingRequest) => {
      const { data } = await apiClient.post<Holding>("/holdings", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
    },
  })
}

export function useAddCashHolding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AddCashRequest) => {
      const { data } = await apiClient.post<Holding>("/holdings/cash", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
    },
  })
}

export function useUpdateHolding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateHoldingRequest }) => {
      const { data } = await apiClient.put<Holding>(`/holdings/${id}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
    },
  })
}

export function useDeleteHolding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/holdings/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
    },
  })
}

export function useImportHoldings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (holdings: unknown[]) => {
      const { data } = await apiClient.post("/holdings/import", holdings)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
    },
  })
}

export function useWithdraw() {
  return useMutation({
    mutationFn: async (payload: WithdrawRequest) => {
      const { data } = await apiClient.post<WithdrawResponse>("/withdraw", payload)
      return data
    },
  })
}

export function useXRayAlert() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/rebalance/xray-alert")
      return data
    },
  })
}

export function useFxExposureAlert() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/currency-exposure/alert")
      return data
    },
  })
}

export function useSaveTelegram() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SaveTelegramRequest) => {
      const { data } = await apiClient.put<TelegramSettings>("/settings/telegram", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "telegram"] })
    },
  })
}

export function useTestTelegram() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/settings/telegram/test")
      return data
    },
  })
}

export function useTriggerDigest() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/digest")
      return data
    },
  })
}

export function useSavePreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SavePreferencesRequest) => {
      const { data } = await apiClient.put<AllocPreferencesResponse>("/settings/preferences", payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "preferences"] })
    },
  })
}
