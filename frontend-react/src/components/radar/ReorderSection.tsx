import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Button } from "@/components/ui/button"
import { useReorderStocks } from "@/api/hooks/useRadar"
import type { RadarStock } from "@/api/types/radar"

const MIN_STOCKS_FOR_REORDER = 2

interface SortableItemProps {
  id: string
}

function SortableItem({ id }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="flex items-center gap-2 rounded border border-border bg-card px-3 py-2 text-sm cursor-grab active:cursor-grabbing select-none"
    >
      <span className="text-muted-foreground">⠿</span>
      <span>{id}</span>
    </div>
  )
}

interface Props {
  stocks: RadarStock[]
}

export function ReorderSection({ stocks }: Props) {
  const { t } = useTranslation()
  const [reorderOn, setReorderOn] = useState(false)
  const [items, setItems] = useState<string[]>(stocks.map((s) => s.ticker))
  const [feedback, setFeedback] = useState<string | null>(null)
  const reorder = useReorderStocks()

  const sensors = useSensors(useSensor(PointerSensor))

  if (stocks.length < MIN_STOCKS_FOR_REORDER) return null

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setItems((prev) => {
        const oldIndex = prev.indexOf(active.id as string)
        const newIndex = prev.indexOf(over.id as string)
        return arrayMove(prev, oldIndex, newIndex)
      })
    }
  }

  const handleSave = () => {
    reorder.mutate(
      { ordered_tickers: items },
      {
        onSuccess: () => {
          setFeedback(t("radar.stock_card.success_order"))
          setReorderOn(false)
        },
        onError: () => setFeedback(t("common.error")),
      },
    )
  }

  const handleToggle = () => {
    if (!reorderOn) {
      // Reset items to current stock order
      setItems(stocks.map((s) => s.ticker))
      setFeedback(null)
    }
    setReorderOn((v) => !v)
  }

  return (
    <div className="mb-3">
      <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
        <input
          type="checkbox"
          checked={reorderOn}
          onChange={handleToggle}
          className="rounded"
          aria-label={t("radar.stock_card.reorder")}
        />
        {t("radar.stock_card.reorder")}
      </label>

      {reorderOn && (
        <div className="mt-2 space-y-1">
          <p className="text-xs text-muted-foreground">{t("radar.stock_card.reorder_hint")}</p>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={items} strategy={verticalListSortingStrategy}>
              {items.map((ticker) => (
                <SortableItem key={ticker} id={ticker} />
              ))}
            </SortableContext>
          </DndContext>
          <div className="flex items-center gap-2 pt-1">
            <Button size="sm" onClick={handleSave} disabled={reorder.isPending}>
              {t("radar.stock_card.save_order")}
            </Button>
            {feedback && <span className="text-xs text-muted-foreground">{feedback}</span>}
          </div>
        </div>
      )}
    </div>
  )
}
