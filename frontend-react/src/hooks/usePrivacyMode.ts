import { create } from "zustand"

/**
 * Single source of truth for privacy mode across the entire app.
 *
 * RULE: All components MUST read privacy state from this store (via `usePrivacyMode`
 * or the `useIsPrivate` convenience selector). Never read `privacy_mode` from the
 * server preferences API directly in UI components.
 *
 * Lifecycle:
 *  1. On app startup, `initialize(serverValue)` hydrates the store from the server.
 *  2. The sidebar toggle calls `toggle()` and also persists the new value to the server.
 */
interface PrivacyState {
  isPrivate: boolean
  toggle: () => void
  /** Sync to the server-persisted value; called on startup and after any server refetch. */
  initialize: (serverValue: boolean) => void
}

export const usePrivacyMode = create<PrivacyState>((set) => ({
  isPrivate: false,
  toggle: () => set((s) => ({ isPrivate: !s.isPrivate })),
  initialize: (serverValue: boolean) => set({ isPrivate: serverValue }),
}))

/** Convenience selector — returns the current privacy boolean. */
export function useIsPrivate(): boolean {
  return usePrivacyMode((s) => s.isPrivate)
}

export function maskMoney(value: number): string {
  if (usePrivacyMode.getState().isPrivate) return "***"
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
}
