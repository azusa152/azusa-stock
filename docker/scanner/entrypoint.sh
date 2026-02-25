#!/bin/sh
set -e

apk add --no-cache curl jq

# Copy scripts to PATH and make them executable
cp /scripts/folio-curl.sh /usr/local/bin/folio-curl.sh
cp /scripts/smart-scan.sh /usr/local/bin/smart-scan.sh
cp /scripts/sync-13f.sh   /usr/local/bin/sync-13f.sh
cp /scripts/take-snapshot.sh /usr/local/bin/take-snapshot.sh
chmod +x \
  /usr/local/bin/folio-curl.sh \
  /usr/local/bin/smart-scan.sh \
  /usr/local/bin/sync-13f.sh \
  /usr/local/bin/take-snapshot.sh

# Persist environment for cron jobs (Alpine crond doesn't inherit env)
printenv | grep FOLIO_API_KEY > /etc/folio.env 2>/dev/null || true

# Run startup tasks immediately (avoids waiting for first cron tick)
/usr/local/bin/smart-scan.sh
echo "$(date) Running startup snapshot..."
/usr/local/bin/take-snapshot.sh || true

# Cron schedule:
#   */15 * * * *       smart scan every 15 min (market-hours-aware)
#   15 21 * * 1-5      closing scan at 21:15 UTC Mon-Fri
#   0 18 * * 0         weekly digest Sunday 18:00 UTC
#   0 */6 * * *        FX alert every 6 hours
#   0 2 * * *          13F sync daily 02:00 UTC (sync-13f.sh handles filing-season logic)
#   0 23 * * *         daily portfolio snapshot 23:00 UTC (after markets close)
(
  echo "*/15 * * * * /usr/local/bin/smart-scan.sh >> /proc/1/fd/1 2>&1"
  echo "15 21 * * 1-5 /usr/local/bin/folio-curl.sh -X POST http://backend:8000/scan > /dev/null 2>&1"
  echo "0 18 * * 0 /usr/local/bin/folio-curl.sh -X POST http://backend:8000/digest >> /proc/1/fd/1 2>&1"
  echo "0 */6 * * * /usr/local/bin/folio-curl.sh -X POST http://backend:8000/currency-exposure/alert > /dev/null 2>&1"
  echo "0 2 * * * /usr/local/bin/sync-13f.sh >> /proc/1/fd/1 2>&1"
  echo "0 23 * * * /usr/local/bin/take-snapshot.sh >> /proc/1/fd/1 2>&1"
) | crontab -

crond -f -l 2
