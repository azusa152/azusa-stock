import { useEffect } from "react"
import { useLocation, Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Download } from "lucide-react"
import i18n from "@/lib/i18n"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useLanguage } from "@/hooks/useLanguage"
import { usePwaInstall } from "@/hooks/use-pwa-install"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { useTheme } from "@/hooks/useTheme"
import { Switch } from "@/components/ui/switch"
import { usePreferences, useSavePreferences } from "@/api/hooks/useAllocation"

const NAV_ITEMS = [
  { path: "/", labelKey: "nav.dashboard", icon: "📊" },
  { path: "/radar", labelKey: "nav.radar", icon: "📡" },
  { path: "/backtest", labelKey: "nav.backtest", icon: "🧪" },
  { path: "/allocation", labelKey: "nav.allocation", icon: "💼" },
  { path: "/fx-watch", labelKey: "nav.fx_watch", icon: "💱" },
  { path: "/smart-money", labelKey: "nav.smart_money", icon: "🏦" },
] as const

export function AppSidebar() {
  const { t } = useTranslation()
  const location = useLocation()
  const { language, changeLanguage, LANGUAGE_OPTIONS } = useLanguage()
  const { canInstall, promptInstall } = usePwaInstall()
  const { isPrivate, toggle, initialize } = usePrivacyMode()
  const { theme, toggle: toggleTheme } = useTheme()
  const { data: prefs } = usePreferences()
  const savePreferences = useSavePreferences()

  // Hydrate privacy mode from server preferences on first load
  useEffect(() => {
    if (prefs?.privacy_mode !== undefined) {
      initialize(prefs.privacy_mode)
    }
  }, [prefs?.privacy_mode, initialize])

  // Hydrate language from server preferences on first load so frontend and
  // backend stay in sync (backend uses the saved language for translated API responses).
  // Use i18n.changeLanguage directly to avoid the write-back API call.
  useEffect(() => {
    if (prefs?.language) {
      i18n.changeLanguage(prefs.language).catch(() => { /* fail silently */ })
    }
  }, [prefs?.language])

  function togglePrivacy() {
    toggle()
    const next = !isPrivate
    savePreferences.mutate(
      { privacy_mode: next },
      { onError: () => { /* fail silently — UI already updated optimistically */ } },
    )
  }

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-3">
        <span className="text-lg font-semibold tracking-tight">📡 Folio</span>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map(({ path, labelKey, icon }) => (
                <SidebarMenuItem key={path}>
                  <SidebarMenuButton asChild isActive={location.pathname === path} className="min-h-[44px]">
                    <Link to={path}>
                      <span>{icon}</span>
                      <span>{t(labelKey)}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-3 py-3 space-y-2">
        {canInstall && (
          <button
            type="button"
            onClick={() => {
              void promptInstall()
            }}
            className="w-full min-h-[44px] px-2 text-xs rounded-md border border-sidebar-border hover:bg-sidebar-accent hover:text-sidebar-accent-foreground inline-flex items-center justify-center gap-2"
          >
            <Download className="h-4 w-4" />
            {t("pwa.install")}
          </button>
        )}
        {/* Dark mode toggle */}
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-muted-foreground">
            {theme === "dark" ? t("common.dark_mode") : t("common.light_mode")}
          </span>
          <button
            onClick={toggleTheme}
            className="text-sm leading-none min-h-[44px] min-w-[44px]"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
        {/* Privacy mode toggle */}
        <div className="flex items-center justify-between px-1 min-h-[44px]">
          <span className="text-xs text-muted-foreground">
            {isPrivate ? t("common.privacy_on") : t("common.privacy_off")}
          </span>
          <div className="min-h-[44px] min-w-[44px] inline-flex items-center justify-center">
            <Switch checked={isPrivate} onCheckedChange={togglePrivacy} />
          </div>
        </div>
        <Select value={language} onValueChange={changeLanguage}>
          <SelectTrigger className="w-full text-xs min-h-[44px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(LANGUAGE_OPTIONS).map(([code, label]) => (
              <SelectItem key={code} value={code} className="text-xs">
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </SidebarFooter>
    </Sidebar>
  )
}
