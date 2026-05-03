#!/bin/sh
set -e

INDEX_FILE="/usr/share/nginx/html/index.html"

if [ -f "$INDEX_FILE" ]; then
    if [ -n "$API_BASE_URL" ]; then
        sed -i "s|%%API_BASE_URL%%|$API_BASE_URL|g" "$INDEX_FILE"
    fi
    if [ -n "$BASALTPASS_BASE_URL" ]; then
        sed -i "s|%%BASALTPASS_BASE_URL%%|$BASALTPASS_BASE_URL|g" "$INDEX_FILE"
    fi
fi

exec "$@"
