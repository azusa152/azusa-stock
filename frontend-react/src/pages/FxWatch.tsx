import { useTranslation } from "react-i18next"

export default function FxWatch() {
  const { t } = useTranslation()
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{t("fx_watch.title")}</h1>
    </div>
  )
}
