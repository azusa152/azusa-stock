#!/bin/sh
# 13F sync: daily in filing season (Feb/May/Aug/Nov), weekly on Mondays off-season.
BACKEND="http://backend:8000"
MONTH=$(date +%m)
DOW=$(date +%u)

case "$MONTH" in
  02|05|08|11)
    echo "$(date) Filing season (month $MONTH) — triggering 13F sync for all gurus..."
    folio-curl.sh -X POST "$BACKEND/gurus/sync" > /dev/null 2>&1
    ;;
  *)
    if [ "$DOW" = "1" ]; then
      echo "$(date) Off-season Monday — triggering weekly 13F sync for amended filings..."
      folio-curl.sh -X POST "$BACKEND/gurus/sync" > /dev/null 2>&1
    else
      echo "$(date) Off-season (month $MONTH, day $DOW) — skipping 13F sync."
    fi
    ;;
esac
