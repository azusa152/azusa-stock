import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { usePreferences, useSavePreferences } from "@/api/hooks/useAllocation"
import { useIsPrivate } from "@/hooks/usePrivacyMode"

const PREF_KEYS = [
  "scan_alerts",
  "price_alerts",
  "weekly_digest",
  "xray_alerts",
  "fx_alerts",
  "fx_watch_alerts",
  "guru_alerts",
]

// Keys that support per-type rate limiting
const RATE_LIMIT_KEYS = ["fx_alerts", "fx_watch_alerts"]

type RateLimitConfig = { max_count: number; window_hours: number }
type RateLimits = Record<string, RateLimitConfig>

const DEFAULT_RATE_LIMIT: RateLimitConfig = { max_count: 0, window_hours: 24 }

export function NotificationPreferences() {
  const { t } = useTranslation()
  const { data } = usePreferences()
  const saveMutation = useSavePreferences()
  const isPrivate = useIsPrivate()

  const [prefs, setPrefs] = useState<Record<string, boolean>>(
    Object.fromEntries(PREF_KEYS.map((k) => [k, true]))
  )
  const [rateLimits, setRateLimits] = useState<RateLimits>({})
  const [feedback, setFeedback] = useState<string | null>(null)
  const [prevData, setPrevData] = useState(data)

  if (prevData !== data) {
    setPrevData(data)
    if (data?.notification_preferences) {
      setPrefs((prev) => ({ ...prev, ...data.notification_preferences }))
    }
    if (data?.notification_rate_limits) {
      setRateLimits(data.notification_rate_limits as RateLimits)
    }
  }

  const handleRateLimitChange = (key: string, field: keyof RateLimitConfig, value: number) => {
    setRateLimits((prev) => ({
      ...prev,
      [key]: {
        ...(prev[key] ?? DEFAULT_RATE_LIMIT),
        [field]: Math.max(0, value),
      },
    }))
  }

  const cleanedRateLimits = (): RateLimits => {
    const cleaned: RateLimits = {}
    for (const [key, rl] of Object.entries(rateLimits)) {
      if (rl.max_count > 0) {
        cleaned[key] = { max_count: rl.max_count, window_hours: rl.window_hours || 24 }
      }
    }
    return cleaned
  }

  const handleSave = () => {
    setFeedback(null)
    const limits = cleanedRateLimits()
    setRateLimits(limits)
    saveMutation.mutate(
      {
        privacy_mode: isPrivate,
        notification_preferences: prefs,
        notification_rate_limits: limits,
      },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          toast.success(t("common.success"))
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      }
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold">{t("allocation.telegram.notif_title")}</p>
      <p className="text-xs text-muted-foreground">{t("allocation.telegram.notif_caption")}</p>

      <div className="space-y-3">
        {PREF_KEYS.map((key) => {
          const isEnabled = prefs[key] ?? true
          const hasRateLimit = RATE_LIMIT_KEYS.includes(key)
          const rl = rateLimits[key] ?? DEFAULT_RATE_LIMIT

          return (
            <div key={key} className="space-y-1.5">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isEnabled}
                  onChange={(e) => setPrefs((prev) => ({ ...prev, [key]: e.target.checked }))}
                  className="rounded mt-0.5 shrink-0"
                />
                <div>
                  <p className="text-xs font-medium">{t(`allocation.telegram.notif.${key}`)}</p>
                  <p className="text-xs text-muted-foreground">{t(`allocation.telegram.notif.${key}_help`)}</p>
                </div>
              </label>

              {hasRateLimit && isEnabled && (
                <div className="ml-6 pl-2 border-l border-border space-y-1">
                  <p className="text-xs text-muted-foreground">
                    {t("allocation.telegram.notif.rate_limit_caption")}
                  </p>
                  <div className="flex items-center gap-3 flex-wrap">
                    <label className="flex items-center gap-1.5">
                      <span className="text-xs text-muted-foreground">
                        {t("allocation.telegram.notif.rate_limit_max")}
                      </span>
                      <input
                        type="number"
                        min={0}
                        value={rl.max_count}
                        onChange={(e) =>
                          handleRateLimitChange(key, "max_count", parseInt(e.target.value) || 0)
                        }
                        className="w-16 h-6 rounded border border-input bg-background px-1.5 text-xs text-center"
                      />
                    </label>
                    {rl.max_count > 0 && (
                      <label className="flex items-center gap-1.5">
                        <span className="text-xs text-muted-foreground">
                          {t("allocation.telegram.notif.rate_limit_window")}
                        </span>
                        <input
                          type="number"
                          min={1}
                          value={rl.window_hours || ""}
                          onChange={(e) => {
                            const raw = parseInt(e.target.value)
                            handleRateLimitChange(key, "window_hours", isNaN(raw) ? 0 : Math.max(1, raw))
                          }}
                          className="w-16 h-6 rounded border border-input bg-background px-1.5 text-xs text-center"
                        />
                      </label>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {rl.max_count === 0
                        ? t("allocation.telegram.notif.rate_limit_unlimited")
                        : t("allocation.telegram.notif.rate_limit_label", {
                            max_count: rl.max_count,
                            window_hours: rl.window_hours,
                          })}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <Button onClick={handleSave} disabled={saveMutation.isPending} size="sm">
        {t("allocation.telegram.save_notif")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}
