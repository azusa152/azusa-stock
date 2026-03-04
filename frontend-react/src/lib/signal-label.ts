import type { TFunction } from "i18next"

export function getSignalLabel(t: TFunction, signal: string): string {
  return t(`config.signal.${signal.toLowerCase()}`, { defaultValue: signal })
}
