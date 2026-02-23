import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FX_CURRENCY_OPTIONS } from "@/lib/constants"
import { useCreateFxWatch } from "@/api/hooks/useFxWatch"

interface Props {
  open: boolean
  onClose: () => void
}

export function AddWatchDialog({ open, onClose }: Props) {
  const { t } = useTranslation()

  const [base, setBase] = useState(FX_CURRENCY_OPTIONS[0])
  const [quote, setQuote] = useState(FX_CURRENCY_OPTIONS[1])
  const [recentHighDays, setRecentHighDays] = useState(30)
  const [consecutiveDays, setConsecutiveDays] = useState(3)
  const [alertOnHigh, setAlertOnHigh] = useState(true)
  const [alertOnConsecutive, setAlertOnConsecutive] = useState(true)
  const [reminderHours, setReminderHours] = useState(24)
  const [error, setError] = useState<string | null>(null)

  const create = useCreateFxWatch()

  const handleSubmit = () => {
    setError(null)
    if (base === quote) {
      setError(t("fx_watch.form.error_same_currency"))
      return
    }
    if (!alertOnHigh && !alertOnConsecutive) {
      setError(t("fx_watch.form.error_no_alert"))
      return
    }
    create.mutate(
      {
        base_currency: base,
        quote_currency: quote,
        recent_high_days: recentHighDays,
        consecutive_increase_days: consecutiveDays,
        alert_on_recent_high: alertOnHigh,
        alert_on_consecutive_increase: alertOnConsecutive,
        reminder_interval_hours: reminderHours,
      },
      {
        onSuccess: () => {
          toast.success(t("common.success"))
          onClose()
        },
        onError: () => {
          setError(t("common.error"))
          toast.error(t("common.error_backend"))
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t("fx_watch.dialog.title")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Currency pair */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">{t("fx_watch.form.base_currency")}</label>
              <Select value={base} onValueChange={setBase}>
                <SelectTrigger className="text-xs h-8 mt-0.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FX_CURRENCY_OPTIONS.map((c) => (
                    <SelectItem key={c} value={c} className="text-xs">{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">{t("fx_watch.form.quote_currency")}</label>
              <Select value={quote} onValueChange={setQuote}>
                <SelectTrigger className="text-xs h-8 mt-0.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FX_CURRENCY_OPTIONS.map((c) => (
                    <SelectItem key={c} value={c} className="text-xs">{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <hr className="border-border" />

          {/* Sliders */}
          <div className="grid grid-cols-2 gap-3">
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
                className="w-full mt-0.5"
              />
            </div>
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
                className="w-full mt-0.5"
              />
            </div>
          </div>

          <hr className="border-border" />

          {/* Alert checkboxes */}
          <div className="grid grid-cols-2 gap-3">
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

          {error && <p className="text-xs text-destructive">{error}</p>}

          <hr className="border-border" />

          <div className="flex gap-2">
            <Button className="flex-1" onClick={handleSubmit} disabled={create.isPending}>
              {t("fx_watch.form.submit")}
            </Button>
            <Button variant="outline" className="flex-1" onClick={onClose}>
              {t("fx_watch.form.cancel")}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
