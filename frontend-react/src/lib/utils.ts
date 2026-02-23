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
