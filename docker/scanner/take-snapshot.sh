#!/bin/sh
# Triggers a daily portfolio snapshot and logs the HTTP status.
# Source environment for cron context (Alpine crond doesn't inherit env).
[ -f /etc/folio.env ] && . /etc/folio.env

BACKEND="http://backend:8000"
echo "$(date) Triggering daily portfolio snapshot..."
if [ -n "$FOLIO_API_KEY" ]; then
  HTTP_STATUS=$(curl -s -m 15 -o /dev/null -w "%{http_code}" -X POST -H "X-API-Key: $FOLIO_API_KEY" "$BACKEND/snapshots/take")
else
  HTTP_STATUS=$(curl -s -m 15 -o /dev/null -w "%{http_code}" -X POST "$BACKEND/snapshots/take")
fi
echo "$(date) Snapshot trigger HTTP status: $HTTP_STATUS"
