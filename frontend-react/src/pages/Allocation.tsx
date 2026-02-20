import { useTranslation } from "react-i18next"

export default function Allocation() {
  const { t } = useTranslation()
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{t("allocation.title")}</h1>
    </div>
  )
}
