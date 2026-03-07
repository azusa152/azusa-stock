import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface GlossaryTermProps {
  termKey: string
  children: ReactNode
  className?: string
}

const TRIGGER_CLASS =
  "inline-flex items-center rounded-sm underline decoration-dotted underline-offset-2 decoration-muted-foreground/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"

export function GlossaryTerm({ termKey, children, className }: GlossaryTermProps) {
  const { t } = useTranslation()
  const i18nKey = `glossary.${termKey}`
  const definition = t(i18nKey)
  const hasDefinition = definition !== i18nKey

  if (!hasDefinition) {
    return <span className={className}>{children}</span>
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={className ?? TRIGGER_CLASS}
            aria-label={definition}
          >
            {children}
          </button>
        </TooltipTrigger>
        <TooltipContent sideOffset={8} className="max-w-64 text-xs leading-relaxed">
          {definition}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
