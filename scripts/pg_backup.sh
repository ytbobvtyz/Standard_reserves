#!/bin/sh
set -eu

POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-standart_reserve}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
FILE="${BACKUP_DIR}/${POSTGRES_DB}_$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$FILE"
date -u +%Y-%m-%dT%H:%M:%SZ > "${BACKUP_DIR}/.last_ok"
echo "Wrote ${FILE}"

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +"$KEEP_DAYS" -delete
