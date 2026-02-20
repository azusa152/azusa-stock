import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClientProvider } from "@tanstack/react-query"
import { queryClient } from "./api/queryClient"
import { AppSidebar } from "./components/layout/AppSidebar"
import { PageShell } from "./components/layout/PageShell"
import { SidebarProvider } from "./components/ui/sidebar"
import { TooltipProvider } from "./components/ui/tooltip"
import Dashboard from "./pages/Dashboard"
import Radar from "./pages/Radar"
import Allocation from "./pages/Allocation"
import FxWatch from "./pages/FxWatch"
import SmartMoney from "./pages/SmartMoney"
import "./lib/i18n"

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <SidebarProvider>
            <div className="flex min-h-screen w-full">
              <AppSidebar />
              <main className="flex-1 overflow-auto">
                <Routes>
                  <Route path="/" element={<PageShell><Dashboard /></PageShell>} />
                  <Route path="/radar" element={<PageShell><Radar /></PageShell>} />
                  <Route path="/allocation" element={<PageShell><Allocation /></PageShell>} />
                  <Route path="/fx-watch" element={<PageShell><FxWatch /></PageShell>} />
                  <Route path="/smart-money" element={<PageShell><SmartMoney /></PageShell>} />
                </Routes>
              </main>
            </div>
          </SidebarProvider>
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
