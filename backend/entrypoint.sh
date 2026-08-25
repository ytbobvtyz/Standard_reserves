#!/bin/sh
set -eu

SECRET_FILE="${SECRET_KEY_FILE:-/var/lib/standart-reserve/secret_key}"
mkdir -p "$(dirname "$SECRET_FILE")"

if [ -z "${SECRET_KEY:-}" ] || [ "${SECRET_KEY}" = "change-me-in-production" ]; then
  if [ -f "$SECRET_FILE" ]; then
    SECRET_KEY="$(cat "$SECRET_FILE")"
  else
    SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
    umask 077
    printf '%s' "$SECRET_KEY" > "$SECRET_FILE"
    echo "Generated SECRET_KEY and saved to ${SECRET_FILE}"
  fi
  export SECRET_KEY
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Applying Alembic migrations..."
  alembic upgrade head
fi

exec "$@"
