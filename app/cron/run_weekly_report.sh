#!/usr/bin/env bash
set -euo pipefail

APP_BASE_URL="${APP_BASE_URL:-https://your-app-domain}"
INTERNAL_API_KEY="${INTERNAL_API_KEY:?INTERNAL_API_KEY env var is required}"

curl -sS -X POST \
  "${APP_BASE_URL}/internal/run-weekly-report" \
  -H "X-Internal-Api-Key: ${INTERNAL_API_KEY}"