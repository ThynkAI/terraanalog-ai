#!/usr/bin/env bash
# Start the FastAPI service and the Next.js UI for local development.
set -euo pipefail
cd "$(dirname "$0")/.."
API_PORT=${API_PORT:-8000}
WEB_PORT=${WEB_PORT:-3000}
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r backend/requirements-dev.txt; }
[ -d web/node_modules ] || (cd web && npm ci)
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "$API_PORT" --reload &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
cd web && API_URL="http://127.0.0.1:$API_PORT" npx next dev -p "$WEB_PORT"
