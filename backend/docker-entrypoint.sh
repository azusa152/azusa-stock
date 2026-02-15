#!/bin/sh
set -e

# Fix ownership of data volume (handles upgrade from root-based containers)
# This is idempotent and runs on every startup.
if [ "$(id -u)" = '0' ]; then
    chown -R folio:folio /app/data
    exec gosu folio "$@"
fi

# Already running as correct user (e.g., in test environments)
exec "$@"
