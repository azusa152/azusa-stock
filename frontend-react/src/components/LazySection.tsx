import { useEffect, useRef, useState, type ReactNode } from "react"

interface Props {
  children: ReactNode
  /** Skeleton or placeholder shown before the section enters the viewport. */
  fallback?: ReactNode
  /**
   * How far outside the viewport to start loading (CSS margin string).
   * "200px" means start loading 200px before the element is visible — so
   * content appears instant when the user scrolls to it.
   */
  rootMargin?: string
}

/**
 * Defers **rendering** of below-fold content until it is near the viewport.
 * This avoids mounting heavy chart components (recharts, lightweight-charts)
 * that are expensive even when invisible.
 *
 * Important: if the wrapped component's data hooks are called in a parent
 * component (e.g. Dashboard), data fetching is NOT deferred — only rendering
 * is. To defer data fetching, use TanStack Query's `enabled` option on the
 * hook at the parent level (e.g. `enabled: !stocksLoading`).
 *
 * Pattern from Vercel Dashboard engineering blog (2022): useInViewport hook +
 * conditional render, combined with a generous rootMargin so content is ready
 * before the user reaches it.
 */
export function LazySection({ children, fallback, rootMargin = "200px" }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Fallback for environments without IntersectionObserver (SSR, old browsers)
    if (!("IntersectionObserver" in window)) {
      const id = setTimeout(() => setVisible(true), 0)
      return () => clearTimeout(id)
    }

    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [rootMargin])

  return <div ref={ref}>{visible ? children : (fallback ?? null)}</div>
}
