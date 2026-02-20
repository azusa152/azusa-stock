import { useLocation, Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
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
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { Switch } from "@/components/ui/switch"

const NAV_ITEMS = [
  { path: "/", labelKey: "nav.dashboard", icon: "📊" },
  { path: "/radar", labelKey: "nav.radar", icon: "📡" },
  { path: "/allocation", labelKey: "nav.allocation", icon: "💼" },
  { path: "/fx-watch", labelKey: "nav.fx_watch", icon: "💱" },
  { path: "/smart-money", labelKey: "nav.smart_money", icon: "🏦" },
] as const

export function AppSidebar() {
  const { t } = useTranslation()
  const location = useLocation()
  const { language, changeLanguage, LANGUAGE_OPTIONS } = useLanguage()
  const { isPrivate, toggle: togglePrivacy } = usePrivacyMode()

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
                  <SidebarMenuButton asChild isActive={location.pathname === path}>
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
        <div className="flex items-center justify-between px-1">
          <span className="text-xs text-muted-foreground">
            {isPrivate ? t("common.privacy_on") : t("common.privacy_off")}
          </span>
          <Switch checked={isPrivate} onCheckedChange={togglePrivacy} />
        </div>
        <Select value={language} onValueChange={changeLanguage}>
          <SelectTrigger className="w-full text-xs">
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
