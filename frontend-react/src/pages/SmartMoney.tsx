import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { useGurus, useSyncAllGurus } from "@/api/hooks/useSmartMoney"
import { OverviewTab } from "@/components/smartmoney/OverviewTab"
import { GuruTab } from "@/components/smartmoney/GuruTab"
import { GrandPortfolioTab } from "@/components/smartmoney/GrandPortfolioTab"
import { AddGuruForm } from "@/components/smartmoney/AddGuruForm"
import { cn } from "@/lib/utils"

const OVERVIEW_TAB = "overview"
const GRAND_PORTFOLIO_TAB = "grand_portfolio"
const ADD_GURU_TAB = "add_guru"

export default function SmartMoney() {
  const { t } = useTranslation()
  const [sopOpen, setSopOpen] = useState(false)
  const [activeTab, setActiveTab] = useState(OVERVIEW_TAB)
  const [styleFilter, setStyleFilter] = useState<string | null>(null)

  const { data: gurus, isLoading, isError } = useGurus()
  const syncAllMutation = useSyncAllGurus()
  const tabsListRef = useRef<HTMLDivElement>(null)

  const activeGurus = gurus?.filter((g) => g.is_active) ?? []
  const filteredGurus = activeGurus.filter(
    (g) => styleFilter == null || g.style === styleFilter,
  )
  const filteredGuruIds = new Set(filteredGurus.map((g) => String(g.id)))
  const resolvedTab =
    activeTab !== OVERVIEW_TAB &&
    activeTab !== GRAND_PORTFOLIO_TAB &&
    activeTab !== ADD_GURU_TAB &&
    !filteredGuruIds.has(activeTab)
      ? OVERVIEW_TAB
      : activeTab

  useEffect(() => {
    if (!tabsListRef.current) return
    const activeEl = tabsListRef.current.querySelector<HTMLElement>(
      `[data-state="active"]`,
    )
    activeEl?.scrollIntoView({ inline: "nearest", block: "nearest" })
  }, [resolvedTab])

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

  const availableStyles: string[] = Array.from(
    new Set(activeGurus.map((g) => g.style).filter((s): s is string => !!s)),
  )

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

      {/* Style filter chips */}
      {availableStyles.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setStyleFilter(null)}
            className={cn(
              "text-xs px-2 py-0.5 rounded-full border transition-colors",
              styleFilter == null ? "bg-foreground text-background" : "hover:bg-muted/50",
            )}
          >
            {t("smart_money.filter.all_styles")}
          </button>
          {availableStyles.map((s) => (
            <button
              key={s}
              onClick={() => setStyleFilter(s === styleFilter ? null : s)}
              className={cn(
                "text-xs px-2 py-0.5 rounded-full border transition-colors",
                s === styleFilter ? "bg-foreground text-background" : "hover:bg-muted/50",
              )}
            >
              {t(`guru_style.${s.toLowerCase()}`, { defaultValue: s })}
            </button>
          ))}
        </div>
      )}

      {/* Tab bar: Overview + Grand Portfolio + per-guru + Add Guru */}
      <Tabs value={resolvedTab} onValueChange={setActiveTab}>
        <ScrollArea className="w-full">
          <TabsList ref={tabsListRef} className="inline-flex w-max gap-1">
            <TabsTrigger value={OVERVIEW_TAB}>{t("smart_money.overview.tab")}</TabsTrigger>
            <TabsTrigger value={GRAND_PORTFOLIO_TAB}>
              {t("smart_money.grand_portfolio.tab")}
            </TabsTrigger>
            {filteredGurus.map((guru) => (
              <TabsTrigger key={guru.id} value={String(guru.id)} data-guru-tab={String(guru.id)}>
                {guru.display_name}
              </TabsTrigger>
            ))}
            <TabsTrigger value={ADD_GURU_TAB}>{t("smart_money.overview.add_guru_tab")}</TabsTrigger>
          </TabsList>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>

        {/* Overview tab */}
        <TabsContent value={OVERVIEW_TAB} className="mt-4">
          {activeGurus.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("smart_money.no_gurus_hint")}</p>
          ) : (
            <OverviewTab />
          )}
        </TabsContent>

        {/* Grand Portfolio tab */}
        <TabsContent value={GRAND_PORTFOLIO_TAB} className="mt-4">
          <GrandPortfolioTab />
        </TabsContent>

        {/* Per-guru tabs */}
        {filteredGurus.map((guru) => (
          <TabsContent key={guru.id} value={String(guru.id)} className="mt-4">
            <GuruTab guruId={guru.id} guruName={guru.display_name} enabled={resolvedTab === String(guru.id)} />
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
