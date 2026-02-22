import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useHoldings, useProfile } from "@/api/hooks/useDashboard"
import { usePreferences } from "@/api/hooks/useAllocation"
import { AddHoldingSheet } from "@/components/allocation/AddHoldingSheet"
import { RebalanceAnalysis } from "@/components/allocation/RebalanceAnalysis"
import { CurrencyExposure } from "@/components/allocation/CurrencyExposure"
import { StressTest } from "@/components/allocation/StressTest"
import { SmartWithdrawal } from "@/components/allocation/SmartWithdrawal"
import { TargetAllocation } from "@/components/allocation/TargetAllocation"
import { HoldingsManager } from "@/components/allocation/HoldingsManager"
import { TelegramSettings } from "@/components/allocation/TelegramSettings"
import { NotificationPreferences } from "@/components/allocation/NotificationPreferences"
import { DISPLAY_CURRENCIES } from "@/lib/constants"

export default function Allocation() {
  const { t } = useTranslation()
  const [sopOpen, setSopOpen] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("portfolio")
  const [displayCurrency, setDisplayCurrency] = useState("USD")

  const { data: profile, isLoading: profileLoading } = useProfile()
  const { data: holdings, isLoading: holdingsLoading } = useHoldings()
  const { data: prefs } = usePreferences()

  const privacyMode = prefs?.privacy_mode ?? false
  const isLoading = profileLoading || holdingsLoading

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-80" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (!profile || !holdings) {
    return (
      <div className="p-6 space-y-3">
        <h1 className="text-2xl font-bold">{t("allocation.title")}</h1>
        <p className="text-sm text-destructive">{t("common.error_backend")}</p>
      </div>
    )
  }

  const hasSetup = holdings.length > 0

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("allocation.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("allocation.caption")}</p>
        </div>
        <Button
          size="sm"
          className="text-xs shrink-0"
          onClick={() => setSheetOpen(true)}
        >
          {t("allocation.sidebar.add_holding")}
        </Button>
      </div>

      {/* SOP collapsible */}
      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          className="w-full text-left px-4 py-2 text-sm font-medium hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("allocation.sop.title")}</span>
          <span className="text-muted-foreground text-xs">{sopOpen ? "▲" : "▼"}</span>
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("allocation.sop.content")}
            </div>
          </div>
        )}
      </div>

      {/* Setup guard — show hint when no holdings but still show Settings tab */}
      {!hasSetup && (
        <div className="rounded-md border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-700 dark:text-yellow-400">
          {t("allocation.setup_required")}
        </div>
      )}

      {/* Main tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="portfolio">{t("allocation.tab.portfolio")}</TabsTrigger>
          <TabsTrigger value="risk">{t("allocation.tab.risk")}</TabsTrigger>
          <TabsTrigger value="actions">{t("allocation.tab.actions")}</TabsTrigger>
          <TabsTrigger value="settings">{t("allocation.tab.settings")}</TabsTrigger>
        </TabsList>

        {/* Portfolio tab */}
        <TabsContent value="portfolio" className="mt-4 space-y-4">
          {/* Display currency selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">{t("allocation.display_currency")}</span>
            <select
              value={displayCurrency}
              onChange={(e) => setDisplayCurrency(e.target.value)}
              className="text-xs border border-border rounded px-2 py-1 bg-background"
            >
              {DISPLAY_CURRENCIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <RebalanceAnalysis displayCurrency={displayCurrency} privacyMode={privacyMode} enabled={activeTab === "portfolio"} />
        </TabsContent>

        {/* Risk tab */}
        <TabsContent value="risk" className="mt-4 space-y-6">
          <CurrencyExposure privacyMode={privacyMode} profile={profile} enabled={activeTab === "risk"} />
          <hr className="border-border" />
          <StressTest displayCurrency={displayCurrency} privacyMode={privacyMode} enabled={activeTab === "risk"} />
        </TabsContent>

        {/* Actions tab */}
        <TabsContent value="actions" className="mt-4">
          <SmartWithdrawal privacyMode={privacyMode} />
        </TabsContent>

        {/* Settings tab */}
        <TabsContent value="settings" className="mt-4 space-y-8">
          <TargetAllocation />
          <hr className="border-border" />
          <HoldingsManager privacyMode={privacyMode} />
          <hr className="border-border" />
          <TelegramSettings privacyMode={privacyMode} />
          <hr className="border-border" />
          <NotificationPreferences />
        </TabsContent>
      </Tabs>

      {/* Add Holding sidebar sheet */}
      <AddHoldingSheet open={sheetOpen} onClose={() => setSheetOpen(false)} />
    </div>
  )
}
