import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useRegisterSW } from "virtual:pwa-register/react"

const OFFLINE_READY_TOAST_ID = "pwa-offline-ready"
const UPDATE_AVAILABLE_TOAST_ID = "pwa-update-available"

export function ReloadPrompt() {
  const { t } = useTranslation()
  const updateIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isMountedRef = useRef(true)
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_swUrl, registration) {
      if (!registration || !isMountedRef.current) return
      if (updateIntervalRef.current) {
        clearInterval(updateIntervalRef.current)
      }
      updateIntervalRef.current = setInterval(() => {
        registration.update()
      }, 60 * 60 * 1000)
    },
  })

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      if (updateIntervalRef.current) {
        clearInterval(updateIntervalRef.current)
        updateIntervalRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!offlineReady) return
    toast.success(t("pwa.offline_ready"), { id: OFFLINE_READY_TOAST_ID })
    setOfflineReady(false)
  }, [offlineReady, setOfflineReady, t])

  useEffect(() => {
    if (!needRefresh) return
    toast(t("pwa.new_content"), {
      id: UPDATE_AVAILABLE_TOAST_ID,
      action: {
        label: t("pwa.update"),
        onClick: () => updateServiceWorker(true),
      },
      duration: Infinity,
      onDismiss: () => setNeedRefresh(false),
    })
  }, [needRefresh, setNeedRefresh, t, updateServiceWorker])

  return null
}
