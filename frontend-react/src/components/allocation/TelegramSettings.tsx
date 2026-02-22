import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useTelegramSettings, useSaveTelegram, useTestTelegram, useTriggerDigest } from "@/api/hooks/useAllocation"

interface Props {
  privacyMode: boolean
}

export function TelegramSettings({ privacyMode }: Props) {
  const { t } = useTranslation()
  const { data } = useTelegramSettings()
  const saveMutation = useSaveTelegram()
  const testMutation = useTestTelegram()
  const digestMutation = useTriggerDigest()

  const [editOpen, setEditOpen] = useState(false)
  const [chatId, setChatId] = useState("")
  const [token, setToken] = useState("")
  const [useCustom, setUseCustom] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)

  const handleEditOpen = () => {
    setChatId(data?.telegram_chat_id ?? "")
    setToken("")
    setUseCustom(data?.use_custom_bot ?? false)
    setEditOpen(true)
  }

  const handleSave = () => {
    setFeedback(null)
    saveMutation.mutate(
      {
        telegram_chat_id: chatId,
        custom_bot_token: token || undefined,
        use_custom_bot: useCustom,
      },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          setEditOpen(false)
        },
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  const handleTest = () => {
    setFeedback(null)
    testMutation.mutate(undefined, {
      onSuccess: () => setFeedback(t("common.success")),
      onError: () => setFeedback(t("common.error")),
    })
  }

  const handleDigest = () => {
    setFeedback(null)
    digestMutation.mutate(undefined, {
      onSuccess: () => setFeedback(t("common.success")),
      onError: () => setFeedback(t("common.error")),
    })
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold">{t("allocation.telegram.title")}</p>
      <p className="text-xs text-muted-foreground">{t("allocation.telegram.caption")}</p>

      {data && (
        <div className="grid grid-cols-2 gap-2 text-xs max-w-sm">
          <div>
            <p className="text-muted-foreground">{t("allocation.telegram.mode")}</p>
            <p className="font-semibold">
              {data.use_custom_bot ? t("allocation.telegram.mode_custom") : t("allocation.telegram.mode_default")}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">{t("allocation.telegram.chat_id")}</p>
            <p className="font-semibold">
              {privacyMode ? "***" : (data.telegram_chat_id || t("allocation.telegram.not_set"))}
            </p>
          </div>
          {data.use_custom_bot && (
            <div>
              <p className="text-muted-foreground">{t("allocation.telegram.custom_token")}</p>
              <p className="font-semibold">{data.custom_bot_token_masked || t("allocation.telegram.not_set")}</p>
            </div>
          )}
        </div>
      )}

      {/* Edit collapsible */}
      <button
        onClick={() => editOpen ? setEditOpen(false) : handleEditOpen()}
        className="text-xs text-primary hover:underline flex items-center gap-1"
      >
        {t("allocation.telegram.edit_title")} {editOpen ? "▲" : "▼"}
      </button>

      {editOpen && (
        <div className="space-y-3 max-w-sm pl-2 border-l border-border">
          <div className="space-y-1">
            <label className="text-xs font-medium">{t("allocation.telegram.chat_id_input")}</label>
            <Input
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              placeholder={t("allocation.telegram.chat_id_placeholder")}
              className="text-xs"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium">{t("allocation.telegram.token_input")}</label>
            <Input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              type="password"
              placeholder={t("allocation.telegram.token_placeholder")}
              className="text-xs"
            />
          </div>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={useCustom}
              onChange={(e) => setUseCustom(e.target.checked)}
              className="rounded"
            />
            {t("allocation.telegram.use_custom")}
          </label>
          <p className="text-xs text-muted-foreground">{t("allocation.telegram.hint")}</p>
          <Button onClick={handleSave} disabled={saveMutation.isPending} size="sm">
            {t("allocation.telegram.save_button")}
          </Button>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 flex-wrap">
        <Button size="sm" variant="outline" className="text-xs" onClick={handleTest} disabled={testMutation.isPending}>
          {t("allocation.telegram.test_button")}
        </Button>
        <Button size="sm" variant="outline" className="text-xs" onClick={handleDigest} disabled={digestMutation.isPending}>
          {t("allocation.telegram.digest_button")}
        </Button>
      </div>

      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}
