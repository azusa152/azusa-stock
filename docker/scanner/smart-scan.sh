#!/bin/sh
# Market-hours aware scanner: only triggers a scan if data is stale (>= 15 min).
# Source environment for cron context (Alpine crond doesn't inherit env).
[ -f /etc/folio.env ] && . /etc/folio.env

BACKEND="http://backend:8000"
STALE_SECONDS=900

# Market-hours gate: skip scans on weekends and outside extended US market hours
DOW=$(date +%u)   # 1=Mon ... 7=Sun
HOUR=$(date -u +%H)  # UTC hour (0-23)

if [ "$DOW" -ge 6 ]; then
  echo "$(date) Weekend — skipping scan."
  exit 0
fi

# Extended US market window: 13:00-22:00 UTC (pre-market 08:00 ET to post-close 18:00 ET)
if [ "$HOUR" -lt 13 ] || [ "$HOUR" -ge 22 ]; then
  echo "$(date) Off-market hours (UTC $HOUR) — skipping scan."
  exit 0
fi

last_epoch=$(folio-curl.sh "$BACKEND/scan/last" | jq -r '.epoch // empty')
if [ -z "$last_epoch" ]; then
  echo "$(date) No previous scan found, triggering scan..."
  folio-curl.sh -X POST "$BACKEND/scan" > /dev/null 2>&1
  exit 0
fi

now_epoch=$(date +%s)
age=$(( now_epoch - last_epoch ))

if [ "$age" -ge "$STALE_SECONDS" ]; then
  echo "$(date) Last scan was ${age}s ago (>= ${STALE_SECONDS}s), triggering scan..."
  folio-curl.sh -X POST "$BACKEND/scan" > /dev/null 2>&1
else
  echo "$(date) Last scan was ${age}s ago (< ${STALE_SECONDS}s), skipping."
fi
