#!/bin/sh
set -eu

DOMAIN="${DOMAIN:-localhost}"
CERT_DIR="${CERT_DIR:-/etc/nginx/certs}"
mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
  echo "TLS certificates not found; generating a self-signed certificate for ${DOMAIN}"
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/CN=${DOMAIN}"
fi

export DOMAIN
envsubst '${DOMAIN}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
nginx -t
