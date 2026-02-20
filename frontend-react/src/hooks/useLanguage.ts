import { useTranslation } from "react-i18next"
import apiClient from "@/api/client"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"

const LANGUAGE_OPTIONS = {
  "zh-TW": "🇹🇼 繁體中文",
  en: "🇺🇸 English",
  ja: "🇯🇵 日本語",
  "zh-CN": "🇨🇳 简体中文",
} as const

export function useLanguage() {
  const { i18n } = useTranslation()

  const changeLanguage = async (lang: string) => {
    await i18n.changeLanguage(lang)
    try {
      await apiClient.put("/settings/preferences", {
        language: lang,
        privacy_mode: usePrivacyMode.getState().isPrivate,
      })
    } catch {
      /* fail silently */
    }
  }

  return { language: i18n.language, changeLanguage, LANGUAGE_OPTIONS }
}
