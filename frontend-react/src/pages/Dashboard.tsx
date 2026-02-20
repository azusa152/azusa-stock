import { useTranslation } from "react-i18next"

export default function Dashboard() {
  const { t } = useTranslation()
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{t("dashboard.title")}</h1>
      <p className="text-muted-foreground mt-2">{t("dashboard.welcome")}</p>
    </div>
  )
}
