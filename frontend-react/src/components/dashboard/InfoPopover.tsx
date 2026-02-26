import type { ReactNode } from "react"
import { CircleHelp } from "lucide-react"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"

interface InfoPopoverProps {
  children: ReactNode
  align?: "start" | "center" | "end"
}

export function InfoPopover({ children, align = "start" }: InfoPopoverProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center text-muted-foreground/40 hover:text-muted-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
          aria-label="More info"
        >
          <CircleHelp className="h-3.5 w-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align={align} className="text-sm space-y-2 w-80">
        {children}
      </PopoverContent>
    </Popover>
  )
}
