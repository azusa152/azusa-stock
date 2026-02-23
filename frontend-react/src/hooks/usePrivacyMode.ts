import { create } from "zustand"

interface PrivacyState {
  isPrivate: boolean
  toggle: () => void
}

export const usePrivacyMode = create<PrivacyState>((set) => ({
  isPrivate: false,
  toggle: () => set((s) => ({ isPrivate: !s.isPrivate })),
}))

export function maskMoney(value: number): string {
  if (usePrivacyMode.getState().isPrivate) return "***"
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
}
