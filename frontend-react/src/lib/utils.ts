import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Parse a backend ISO timestamp as UTC and return a Date object.
 *
 * The backend serialises datetimes without a timezone suffix
 * (e.g. "2026-02-23T08:36:17"). Per the ES spec, the browser's Date
 * constructor treats such naive date-time strings as LOCAL time, not UTC.
 * To ensure the timestamp is correctly interpreted as UTC, we append "Z"
 * when no timezone offset is present.
 */
export function parseUtc(iso: string): Date {
  const withTz = iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`
  return new Date(withTz)
}

/**
 * Format a backend UTC ISO timestamp in the user's local timezone.
 */
export function formatLocalTime(iso: string): string {
  return parseUtc(iso).toLocaleString()
}

const relativeTimeFormatterCache = new Map<string, Intl.RelativeTimeFormat>()

function getRelativeTimeFormatter(locale?: string): Intl.RelativeTimeFormat {
  const cacheKey = locale ?? ""
  const cached = relativeTimeFormatterCache.get(cacheKey)
  if (cached) return cached

  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" })
  relativeTimeFormatterCache.set(cacheKey, formatter)
  return formatter
}

/**
 * Format elapsed seconds into a localized relative time string.
 */
export function formatRelativeTime(seconds: number, locale?: string): string {
  if (!Number.isFinite(seconds)) return ""
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const rtf = getRelativeTimeFormatter(locale)

  if (safeSeconds < 60 * 60) {
    const minutes = Math.max(1, Math.floor(safeSeconds / 60))
    return rtf.format(-minutes, "minute")
  }

  if (safeSeconds < 24 * 60 * 60) {
    const hours = Math.max(1, Math.floor(safeSeconds / (60 * 60)))
    return rtf.format(-hours, "hour")
  }

  const days = Math.max(1, Math.floor(safeSeconds / (24 * 60 * 60)))
  return rtf.format(-days, "day")
}
