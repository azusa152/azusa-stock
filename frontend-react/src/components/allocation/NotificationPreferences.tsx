import { useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { usePreferences, useSavePreferences } from "@/api/hooks/useAllocation"

const PREF_KEYS = ["scan_alerts", "price_alerts", "weekly_digest", "xray_alerts", "fx_alerts"]

export function NotificationPreferences() {
  const { t } = useTranslation()
  const { data } = usePreferences()
  const saveMutation = useSavePreferences()

  const [prefs, setPrefs] = useState<Record<string, boolean>>(
    Object.fromEntries(PREF_KEYS.map((k) => [k, true]))
  )
  const [feedback, setFeedback] = useState<string | null>(null)

  useEffect(() => {
    if (data?.notification_preferences) {
      setPrefs((prev) => ({ ...prev, ...data.notification_preferences }))
    }
  }, [data])

  const handleSave = () => {
    setFeedback(null)
    saveMutation.mutate(
      { notification_preferences: prefs },
      {
        onSuccess: () => setFeedback(t("common.success")),
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold">{t("allocation.telegram.notif_title")}</p>
      <p className="text-xs text-muted-foreground">{t("allocation.telegram.notif_caption")}</p>

      <div className="space-y-3">
        {PREF_KEYS.map((key) => (
          <label key={key} className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={prefs[key] ?? true}
              onChange={(e) => setPrefs((prev) => ({ ...prev, [key]: e.target.checked }))}
              className="rounded mt-0.5 shrink-0"
            />
            <div>
              <p className="text-xs font-medium">{t(`allocation.telegram.notif.${key}`)}</p>
              <p className="text-xs text-muted-foreground">{t(`allocation.telegram.notif.${key}_help`)}</p>
            </div>
          </label>
        ))}
      </div>

      <Button onClick={handleSave} disabled={saveMutation.isPending} size="sm">
        {t("allocation.telegram.save_notif")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}
