#!/usr/bin/env sh
# Container entrypoint for py-server.
#
# Plain HTTP is the default. TLS is enabled only when BOTH SSL_CERTFILE and
# SSL_KEYFILE are provided and readable; certificates are never baked into
# the image and must be mounted at runtime. Uvicorn auto-reload is opt-in and
# intended for local development only.
set -eu

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

set -- uvicorn main:app --host "$HOST" --port "$PORT"

if [ -n "${SSL_CERTFILE:-}" ] || [ -n "${SSL_KEYFILE:-}" ]; then
    if [ -z "${SSL_CERTFILE:-}" ] || [ -z "${SSL_KEYFILE:-}" ]; then
        echo "TLS misconfigured: set both SSL_CERTFILE and SSL_KEYFILE (or neither)." >&2
        exit 1
    fi
    if [ ! -f "$SSL_CERTFILE" ] || [ ! -f "$SSL_KEYFILE" ]; then
        echo "TLS enabled but certificate material is not readable: cert=$SSL_CERTFILE key=$SSL_KEYFILE" >&2
        exit 1
    fi
    set -- "$@" --ssl-certfile "$SSL_CERTFILE" --ssl-keyfile "$SSL_KEYFILE"
fi

if [ "${UVICORN_RELOAD:-0}" = "1" ]; then
    set -- "$@" --reload
fi

exec "$@"
