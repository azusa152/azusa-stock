import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClientProvider } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { Toaster } from "sonner"
import { queryClient } from "./api/queryClient"
import { AppSidebar } from "./components/layout/AppSidebar"
import { PageShell } from "./components/layout/PageShell"
import { SidebarProvider, SidebarTrigger } from "./components/ui/sidebar"
import { TooltipProvider } from "./components/ui/tooltip"
import Dashboard from "./pages/Dashboard"
import Radar from "./pages/Radar"
import Allocation from "./pages/Allocation"
import FxWatch from "./pages/FxWatch"
import SmartMoney from "./pages/SmartMoney"
import Backtest from "./pages/Backtest"
import { ReloadPrompt } from "./components/pwa/ReloadPrompt"
import "./lib/i18n"

export default function App() {
  const { t } = useTranslation()
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <SidebarProvider>
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:text-sm focus:shadow-lg"
            >
              {t("accessibility.skip_to_content")}
            </a>
            <div className="flex min-h-screen w-full">
              <AppSidebar />
              <main id="main-content" tabIndex={-1} className="flex-1 overflow-auto min-w-0 focus:outline-none">
                {/* Mobile header with hamburger trigger */}
                <div className="md:hidden flex items-center gap-2 px-4 py-3 border-b border-border sticky top-0 bg-background z-10">
                  <SidebarTrigger className="min-h-[44px] min-w-[44px]" />
                  <span className="text-sm font-semibold">📡 Folio</span>
                </div>
                <Routes>
                  <Route path="/" element={<PageShell><Dashboard /></PageShell>} />
                  <Route path="/radar" element={<PageShell><Radar /></PageShell>} />
                  <Route path="/allocation" element={<PageShell><Allocation /></PageShell>} />
                  <Route path="/fx-watch" element={<PageShell><FxWatch /></PageShell>} />
                  <Route path="/smart-money" element={<PageShell><SmartMoney /></PageShell>} />
                  <Route path="/backtest" element={<PageShell><Backtest /></PageShell>} />
                </Routes>
              </main>
            </div>
            <Toaster richColors position="bottom-right" />
            <ReloadPrompt />
          </SidebarProvider>
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
