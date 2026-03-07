import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface EmptyStateAction {
  label: string
  onClick: () => void
  variant?: "default" | "outline"
}

interface Props {
  icon?: string
  /** Legacy single-line message (kept for backward compatibility) */
  message: string
  title?: string
  description?: string
  action?: EmptyStateAction
  secondaryAction?: EmptyStateAction
  className?: string
}

export function EmptyState({
  icon = "📭",
  message,
  title,
  description,
  action,
  secondaryAction,
  className,
}: Props) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 py-10 text-center", className)}>
      <p className="text-3xl">{icon}</p>
      {title && <p className="text-base font-semibold">{title}</p>}
      <p className="text-sm text-muted-foreground max-w-md">
        {description ?? message}
      </p>
      {(action || secondaryAction) && (
        <div className="flex items-center gap-2 mt-1">
          {action && (
            <Button
              size="sm"
              variant={action.variant ?? "default"}
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              size="sm"
              variant={secondaryAction.variant ?? "outline"}
              onClick={secondaryAction.onClick}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
