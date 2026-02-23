import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useGurus, useSyncAllGurus } from "@/api/hooks/useSmartMoney"
import { OverviewTab } from "@/components/smartmoney/OverviewTab"
import { GuruTab } from "@/components/smartmoney/GuruTab"
import { AddGuruForm } from "@/components/smartmoney/AddGuruForm"

const OVERVIEW_TAB = "overview"
const ADD_GURU_TAB = "add_guru"

export default function SmartMoney() {
  const { t } = useTranslation()
  const [sopOpen, setSopOpen] = useState(false)
  const [activeTab, setActiveTab] = useState(OVERVIEW_TAB)

  const { data: gurus, isLoading, isError } = useGurus()
  const syncAllMutation = useSyncAllGurus()

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

  if (isError || !gurus) {
    return (
      <div className="p-6 space-y-3">
        <h1 className="text-2xl font-bold">{t("smart_money.title")}</h1>
        <p className="text-sm text-destructive">{t("common.error_backend")}</p>
      </div>
    )
  }

  const activeGurus = gurus.filter((g) => g.is_active)

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("smart_money.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("smart_money.caption")}</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="text-xs shrink-0"
          onClick={() => syncAllMutation.mutate()}
          disabled={syncAllMutation.isPending || activeGurus.length === 0}
        >
          {syncAllMutation.isPending
            ? t("smart_money.sidebar.syncing")
            : t("smart_money.sidebar.sync_button")}
        </Button>
      </div>

      {/* SOP collapsible */}
      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          className="w-full text-left px-4 py-2 text-sm font-medium hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("smart_money.sop.title")}</span>
          <span className="text-muted-foreground text-xs">{sopOpen ? "▲" : "▼"}</span>
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("smart_money.sop.content")}
            </div>
          </div>
        )}
      </div>

      {/* Sync feedback */}
      {syncAllMutation.isSuccess && (
        <p className="text-xs text-muted-foreground">{t("smart_money.sidebar.sync_success")}</p>
      )}
      {syncAllMutation.isError && (
        <p className="text-xs text-destructive">
          {t("smart_money.sidebar.sync_error", { msg: "" })}
        </p>
      )}

      {/* Tab bar: Overview + per-guru + Add Guru */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value={OVERVIEW_TAB}>{t("smart_money.overview.tab")}</TabsTrigger>
          {activeGurus.map((guru) => (
            <TabsTrigger key={guru.id} value={String(guru.id)}>
              {guru.display_name}
            </TabsTrigger>
          ))}
          <TabsTrigger value={ADD_GURU_TAB}>{t("smart_money.overview.add_guru_tab")}</TabsTrigger>
        </TabsList>

        {/* Overview tab */}
        <TabsContent value={OVERVIEW_TAB} className="mt-4">
          {activeGurus.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("smart_money.no_gurus_hint")}</p>
          ) : (
            <OverviewTab />
          )}
        </TabsContent>

        {/* Per-guru tabs */}
        {activeGurus.map((guru) => (
          <TabsContent key={guru.id} value={String(guru.id)} className="mt-4">
            <GuruTab guruId={guru.id} guruName={guru.display_name} enabled={activeTab === String(guru.id)} />
          </TabsContent>
        ))}

        {/* Add Guru tab */}
        <TabsContent value={ADD_GURU_TAB} className="mt-4">
          <AddGuruForm onSuccess={() => setActiveTab(OVERVIEW_TAB)} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
