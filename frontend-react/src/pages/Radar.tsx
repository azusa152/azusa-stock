import { useTranslation } from "react-i18next"

export default function Radar() {
  const { t } = useTranslation()
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{t("radar.title")}</h1>
    </div>
  )
}
