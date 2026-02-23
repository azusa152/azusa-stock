import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { useUpdateFxWatch } from "@/api/hooks/useFxWatch"
import type { FxWatch } from "@/api/types/fxWatch"

interface Props {
  watch: FxWatch
}

export function EditWatchPopover({ watch }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [recentHighDays, setRecentHighDays] = useState(watch.recent_high_days)
  const [consecutiveDays, setConsecutiveDays] = useState(watch.consecutive_increase_days)
  const [alertOnHigh, setAlertOnHigh] = useState(watch.alert_on_recent_high)
  const [alertOnConsecutive, setAlertOnConsecutive] = useState(watch.alert_on_consecutive_increase)
  const [reminderHours, setReminderHours] = useState(watch.reminder_interval_hours)
  const [feedback, setFeedback] = useState<string | null>(null)

  const update = useUpdateFxWatch()

  // Reset form state when popover opens or watched config changes
  const [prevOpen, setPrevOpen] = useState(open)
  const [prevWatch, setPrevWatch] = useState(watch)
  if (prevOpen !== open || prevWatch !== watch) {
    setPrevOpen(open)
    setPrevWatch(watch)
    if (open) {
      setRecentHighDays(watch.recent_high_days)
      setConsecutiveDays(watch.consecutive_increase_days)
      setAlertOnHigh(watch.alert_on_recent_high)
      setAlertOnConsecutive(watch.alert_on_consecutive_increase)
      setReminderHours(watch.reminder_interval_hours)
      setFeedback(null)
    }
  }

  const handleSave = () => {
    if (!alertOnHigh && !alertOnConsecutive) {
      setFeedback(t("fx_watch.form.error_no_alert"))
      return
    }
    update.mutate(
      {
        id: watch.id,
        payload: {
          recent_high_days: recentHighDays,
          consecutive_increase_days: consecutiveDays,
          alert_on_recent_high: alertOnHigh,
          alert_on_consecutive_increase: alertOnConsecutive,
          reminder_interval_hours: reminderHours,
        },
      },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          toast.success(t("common.success"))
          setOpen(false)
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      },
    )
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button size="sm" variant="outline" className="text-xs">
          {t("fx_watch.edit.button")}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 space-y-3 p-4" align="start">
        <p className="text-sm font-semibold">
          {t("fx_watch.edit.title", { pair: `${watch.base_currency}/${watch.quote_currency}` })}
        </p>

        {/* Recent high days */}
        <div>
          <label className="text-xs text-muted-foreground">
            {t("fx_watch.form.recent_high_days")}: {recentHighDays}
          </label>
          <input
            type="range"
            min={5}
            max={90}
            step={5}
            value={recentHighDays}
            onChange={(e) => setRecentHighDays(Number(e.target.value))}
            className="w-full"
          />
        </div>

        {/* Consecutive days */}
        <div>
          <label className="text-xs text-muted-foreground">
            {t("fx_watch.form.consecutive_days")}: {consecutiveDays}
          </label>
          <input
            type="range"
            min={2}
            max={10}
            step={1}
            value={consecutiveDays}
            onChange={(e) => setConsecutiveDays(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <hr className="border-border" />

        {/* Alert checkboxes */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={alertOnHigh}
              onChange={(e) => setAlertOnHigh(e.target.checked)}
            />
            {t("fx_watch.form.alert_on_high")}
          </label>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={alertOnConsecutive}
              onChange={(e) => setAlertOnConsecutive(e.target.checked)}
            />
            {t("fx_watch.form.alert_on_consecutive")}
          </label>
        </div>

        {/* Reminder hours */}
        <div>
          <label className="text-xs text-muted-foreground">{t("fx_watch.form.reminder_hours")}</label>
          <input
            type="number"
            min={1}
            max={168}
            value={reminderHours}
            onChange={(e) => setReminderHours(Number(e.target.value))}
            className="mt-0.5 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
          />
        </div>

        <Button size="sm" className="w-full" onClick={handleSave} disabled={update.isPending}>
          {t("fx_watch.form.save")}
        </Button>
        {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
      </PopoverContent>
    </Popover>
  )
}
