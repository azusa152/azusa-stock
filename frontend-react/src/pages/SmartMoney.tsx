import { useTranslation } from "react-i18next"

export default function SmartMoney() {
  const { t } = useTranslation()
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{t("smart_money.title")}</h1>
    </div>
  )
}
