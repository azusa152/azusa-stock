import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAddGuru } from "@/api/hooks/useSmartMoney"

interface Props {
  onSuccess: () => void
}

export function AddGuruForm({ onSuccess }: Props) {
  const { t } = useTranslation()
  const [name, setName] = useState("")
  const [cik, setCik] = useState("")
  const [displayName, setDisplayName] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)

  const addMutation = useAddGuru()

  const handleSubmit = () => {
    if (!name.trim() || !cik.trim() || !displayName.trim()) {
      setFeedback(t("smart_money.add_guru.required_warning"))
      return
    }
    setFeedback(null)
    addMutation.mutate(
      { name: name.trim(), cik: cik.trim(), display_name: displayName.trim() },
      {
        onSuccess: () => {
          setFeedback(t("smart_money.add_guru.success", { display_name: displayName.trim() }))
          setName("")
          setCik("")
          setDisplayName("")
          onSuccess()
        },
        onError: () => {
          setFeedback(t("common.error"))
        },
      },
    )
  }

  return (
    <div className="space-y-4 max-w-md">
      <div>
        <h2 className="text-base font-semibold">{t("smart_money.add_guru.title")}</h2>
        <p className="text-xs text-muted-foreground mt-0.5">{t("smart_money.add_guru.description")}</p>
      </div>

      <div className="space-y-3">
        <div className="space-y-1">
          <label className="text-xs font-medium">{t("smart_money.add_guru.name_label")}</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("smart_money.add_guru.name_placeholder")}
            className="text-sm"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">{t("smart_money.add_guru.cik_label")}</label>
          <Input
            value={cik}
            onChange={(e) => setCik(e.target.value)}
            placeholder={t("smart_money.add_guru.cik_placeholder")}
            className="text-sm"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium">{t("smart_money.add_guru.display_label")}</label>
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={t("smart_money.add_guru.display_placeholder")}
            className="text-sm"
          />
        </div>
      </div>

      <Button
        onClick={handleSubmit}
        disabled={addMutation.isPending}
        className="w-full"
      >
        {t("smart_money.add_guru.submit_button")}
      </Button>

      {feedback && (
        <p className="text-xs text-muted-foreground">{feedback}</p>
      )}
    </div>
  )
}
