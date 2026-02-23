import { create } from "zustand"
import { persist } from "zustand/middleware"

type Theme = "light" | "dark"

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggle: () => void
}

export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "light",
      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },
      toggle: () => {
        const next: Theme = get().theme === "dark" ? "light" : "dark"
        set({ theme: next })
        applyTheme(next)
      },
    }),
    {
      name: "folio-theme",
      onRehydrateStorage: () => (state) => {
        if (state) applyTheme(state.theme)
      },
    },
  ),
)

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === "dark") {
    root.classList.add("dark")
  } else {
    root.classList.remove("dark")
  }
}
