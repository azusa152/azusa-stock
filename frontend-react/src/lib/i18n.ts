import i18n from "i18next"
import { initReactI18next } from "react-i18next"
import HttpBackend from "i18next-http-backend"

declare const __APP_VERSION__: string

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    fallbackLng: "zh-TW",
    supportedLngs: ["zh-TW", "en", "ja", "zh-CN"],
    ns: ["translation"],
    defaultNS: "translation",
    backend: {
      loadPath: "/locales/{{lng}}.json",
      queryStringParams: { v: __APP_VERSION__ },
    },
    interpolation: {
      escapeValue: false,
    },
  })

export default i18n
