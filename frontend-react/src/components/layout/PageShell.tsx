import { Suspense } from "react"
import { Skeleton } from "@/components/ui/skeleton"

function PageSkeleton() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-72" />
      <div className="grid grid-cols-3 gap-4 mt-6">
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-24 rounded-lg" />
      </div>
    </div>
  )
}

interface PageShellProps {
  children: React.ReactNode
}

export function PageShell({ children }: PageShellProps) {
  return (
    <div className="mx-auto w-full max-w-7xl">
      <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
    </div>
  )
}
