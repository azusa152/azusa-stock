import { useState, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { useTemplates, useCreateProfile, useUpdateProfile } from "@/api/hooks/useAllocation"
import { useProfile } from "@/api/hooks/useDashboard"
import { STOCK_CATEGORIES } from "@/lib/constants"

function mergeConfig(config: Record<string, unknown>): Record<string, number> {
  const base = Object.fromEntries(STOCK_CATEGORIES.map((c) => [c, 0]))
  for (const [k, v] of Object.entries(config)) {
    if (k in base) base[k] = typeof v === "number" ? v : 0
  }
  return base
}

export function TargetAllocation() {
  const { t } = useTranslation()
  const { data: templates } = useTemplates()
  const { data: profile } = useProfile()
  const createMutation = useCreateProfile()
  const updateMutation = useUpdateProfile()

  const [selectedTemplate, setSelectedTemplate] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)

  // Base values derived from saved profile — re-computed whenever profile loads or changes.
  // This ensures sliders show the correct saved values even when the component mounts
  // after the profile query has already resolved (e.g. inside a lazy TabsContent).
  const profileSliders = useMemo(
    () => (profile?.config ? mergeConfig(profile.config) : Object.fromEntries(STOCK_CATEGORIES.map((c) => [c, 0]))),
    [profile]
  )

  // User edits override the profile base. null = no pending edits, show profileSliders.
  const [userSliders, setUserSliders] = useState<Record<string, number> | null>(null)
  const sliders = userSliders ?? profileSliders

  const total = Object.values(sliders).reduce((a, b) => a + b, 0)
  const remaining = 100 - total

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplate(templateId)
    const tmpl = templates?.find((tmpl) => tmpl.id === templateId)
    if (tmpl?.default_config) {
      setUserSliders(mergeConfig(tmpl.default_config as Record<string, unknown>))
    }
  }

  const handleSliderChange = (cat: string, value: number) => {
    setUserSliders((prev) => ({ ...(prev ?? profileSliders), [cat]: value }))
  }

  const handleSave = () => {
    setFeedback(null)
    const payload = {
      name: profile?.name ?? "My Portfolio",
      home_currency: profile?.home_currency ?? "USD",
      source_template_id: selectedTemplate || undefined,
      config: sliders,
    }
    if (profile) {
      updateMutation.mutate(
        { id: profile.id, payload: { config: sliders } },
        {
          onSuccess: () => {
            setFeedback(t("common.success"))
            toast.success(t("common.success"))
            setUserSliders(null)
          },
          onError: () => {
            setFeedback(t("common.error"))
            toast.error(t("common.error"))
          },
        },
      )
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => {
          setFeedback(t("common.success"))
          toast.success(t("common.success"))
          setUserSliders(null)
        },
        onError: () => {
          setFeedback(t("common.error"))
          toast.error(t("common.error"))
        },
      })
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold">{t("allocation.target.title")}</p>

      {/* Template selector */}
      {templates && templates.length > 0 && (
        <div className="space-y-1">
          <label className="text-xs font-medium">{t("allocation.target.template_label")}</label>
          <select
            value={selectedTemplate}
            onChange={(e) => handleTemplateChange(e.target.value)}
            className="w-full max-w-xs text-xs border border-border rounded px-2 py-1.5 bg-background"
          >
            <option value="">— {t("allocation.target.template_placeholder")} —</option>
            {templates.map((tmpl) => (
              <option key={tmpl.id} value={tmpl.id}>{tmpl.name}</option>
            ))}
          </select>
          {selectedTemplate && (
            <p className="text-xs text-muted-foreground italic">
              {templates.find((tmpl) => tmpl.id === selectedTemplate)?.description}
            </p>
          )}
        </div>
      )}

      {/* Sliders */}
      <div className="space-y-3 max-w-sm">
        {STOCK_CATEGORIES.map((cat) => (
          <div key={cat} className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium">{t(`config.category.${cat.toLowerCase()}`)}</label>
              <span className="text-xs font-semibold">{sliders[cat] ?? 0}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={sliders[cat] ?? 0}
              onChange={(e) => handleSliderChange(cat, Number(e.target.value))}
              className="w-full"
            />
          </div>
        ))}

        {/* Sum validation */}
        <div className={`text-xs font-semibold ${Math.abs(remaining) < 0.01 ? "text-green-600" : "text-yellow-600"}`}>
          {t("allocation.target.sum_label")}: {total.toFixed(0)}% ({remaining >= 0 ? "+" : ""}{remaining.toFixed(0)}% {t("allocation.target.remaining")})
        </div>

        <Button
          onClick={handleSave}
          disabled={createMutation.isPending || updateMutation.isPending || Math.abs(remaining) > 0.5}
          size="sm"
        >
          {t("allocation.target.save_button")}
        </Button>
        {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
      </div>
    </div>
  )
}
