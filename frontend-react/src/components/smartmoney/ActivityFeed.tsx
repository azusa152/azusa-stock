import { useTranslation } from "react-i18next"
import { formatValue } from "./formatters"
import type { ActivityFeed, ActivityFeedItem } from "@/api/types/smartMoney"

function FeedList({ items, emptyKey }: { items: ActivityFeedItem[]; emptyKey: string }) {
  const { t } = useTranslation()
  if (items.length === 0) {
    return <p className="text-xs text-muted-foreground">{t(emptyKey)}</p>
  }
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <div key={item.ticker} className="flex items-start justify-between gap-2 text-xs">
          <div className="min-w-0">
            <span className="font-medium">{item.ticker}</span>
            <span className="text-muted-foreground ml-1 truncate">
              {item.gurus.join(", ")}
            </span>
          </div>
          <div className="shrink-0 text-right">
            <span className="font-medium">
              {item.guru_count} {t("smart_money.activity.guru_count_label")}
            </span>
            <span className="text-muted-foreground ml-1">{formatValue(item.total_value)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

export function ActivityFeed({ data }: { data: ActivityFeed }) {
  const { t } = useTranslation()
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="space-y-2">
        <p className="text-xs font-semibold text-green-600 dark:text-green-400">
          {t("smart_money.activity.most_bought")}
        </p>
        <FeedList items={data.most_bought} emptyKey="smart_money.activity.empty_bought" />
      </div>
      <div className="space-y-2">
        <p className="text-xs font-semibold text-red-600 dark:text-red-400">
          {t("smart_money.activity.most_sold")}
        </p>
        <FeedList items={data.most_sold} emptyKey="smart_money.activity.empty_sold" />
      </div>
    </div>
  )
}
