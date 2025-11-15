#!/usr/bin/env bash
set -euo pipefail

# Config
APP_BASE_URL="${APP_BASE_URL:-https://your-app-domain}"
INTERNAL_API_KEY="${INTERNAL_API_KEY:?INTERNAL_API_KEY env var is required}"

TODAY=$(date +%F)

curl -sS -X POST \
  "${APP_BASE_URL}/internal/run-daily-check?standup_date=${TODAY}" \
  -H "X-Internal-Api-Key: ${INTERNAL_API_KEY}"