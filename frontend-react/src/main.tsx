import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Apply saved theme before first render to avoid flash
;(function () {
  try {
    const stored = localStorage.getItem("folio-theme")
    if (stored) {
      const { state } = JSON.parse(stored)
      if (state?.theme === "dark") document.documentElement.classList.add("dark")
    }
  } catch {
    // ignore
  }
})()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
