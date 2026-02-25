import { useTranslation } from "react-i18next"
import { ACTION_COLORS, ACTION_ICONS } from "./formatters"

interface Props {
  action: string
}

export function ActionBadge({ action }: Props) {
  const { t } = useTranslation()
  const color = ACTION_COLORS[action] ?? ACTION_COLORS.UNCHANGED
  const icon = ACTION_ICONS[action] ?? "⚪"
  const labelKey = `smart_money.action.${action.toLowerCase()}`
  return (
    <span style={{ color }} className="text-xs font-medium whitespace-nowrap">
      {icon} {t(labelKey, { defaultValue: action })}
    </span>
  )
}
