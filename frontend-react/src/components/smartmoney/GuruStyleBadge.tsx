import { useTranslation } from "react-i18next"
import { GURU_STYLE_CONFIG } from "@/lib/constants"
import { cn } from "@/lib/utils"

interface Props {
  style: string | null | undefined
  size?: "sm" | "md"
}

export function GuruStyleBadge({ style, size = "sm" }: Props) {
  const { t } = useTranslation()
  if (!style) return null
  const config = GURU_STYLE_CONFIG[style]
  if (!config) return null
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs",
      )}
      style={{ backgroundColor: `${config.color}20`, color: config.color }}
    >
      {t(`guru_style.${style.toLowerCase()}`, { defaultValue: style })}
    </span>
  )
}
