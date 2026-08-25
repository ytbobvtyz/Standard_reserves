#!/bin/sh
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"

/bin/sh /scripts/pg_backup.sh
while true; do
  sleep "$INTERVAL"
  /bin/sh /scripts/pg_backup.sh
done
