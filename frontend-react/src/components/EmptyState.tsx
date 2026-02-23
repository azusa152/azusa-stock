interface Props {
  icon?: string
  message: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({ icon = "📭", message, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
      <p className="text-3xl">{icon}</p>
      <p className="text-sm text-muted-foreground">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="text-xs text-primary hover:underline"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
