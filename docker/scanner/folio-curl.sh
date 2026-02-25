#!/bin/sh
# Authenticated curl wrapper for the Folio backend API.
# Source environment for cron context (Alpine crond doesn't inherit env).
[ -f /etc/folio.env ] && . /etc/folio.env

if [ -n "$FOLIO_API_KEY" ]; then
  curl -sf -H "X-API-Key: $FOLIO_API_KEY" "$@"
else
  curl -sf "$@"
fi
