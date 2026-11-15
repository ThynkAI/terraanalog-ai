#!/usr/bin/env bash
# TerraAnalog AI — one-command local setup + start (macOS / Linux).
#
#   ./scripts/setup.sh            install deps, build the UI, start API (:8000) + UI (:3000)
#   ./scripts/setup.sh --dev      same, but run the UI with hot reload (next dev)
#   ./scripts/setup.sh --no-start install + build only
#   ./scripts/setup.sh --tests    also install test deps (pytest, Playwright Chromium)
#
# Env overrides: API_PORT (8000), WEB_PORT (3000), TERRA_DATA_DIR (data/research; synthetic fallback data/fixtures), PYTHON (python3).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
API_PORT=${API_PORT:-8000}
WEB_PORT=${WEB_PORT:-3000}
PYTHON=${PYTHON:-python3}
MODE=prod; START=1; TESTS=0
for a in "$@"; do
  case "$a" in
    --dev) MODE=dev ;;
    --no-start) START=0 ;;
    --tests) TESTS=1 ;;
    -h|--help) sed -n 2,10p "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---- prerequisites -------------------------------------------------------------------
command -v "$PYTHON" >/dev/null || die "Python 3.11+ is required (set PYTHON=/path/to/python3)."
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || die "Python 3.11+ is required (found $("$PYTHON" -V 2>&1))."
command -v node >/dev/null || die "Node.js 20+ is required (https://nodejs.org)."
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
[ "$NODE_MAJOR" -ge 20 ] || die "Node.js 20+ is required (found $(node -v))."
command -v npm >/dev/null || die "npm is required (ships with Node.js)."
say "Python $("$PYTHON" -V 2>&1 | cut -d' ' -f2), Node $(node -v)"

# ---- backend -------------------------------------------------------------------------
if [ ! -x .venv/bin/python ]; then
  say "Creating Python virtualenv in .venv"
  "$PYTHON" -m venv .venv
fi
say "Installing backend dependencies"
.venv/bin/python -m pip install -q --upgrade pip
if [ "$TESTS" = 1 ]; then .venv/bin/python -m pip install -q -r backend/requirements-dev.txt; else .venv/bin/python -m pip install -q -r backend/requirements.txt; fi
.venv/bin/python scripts/validate_data.py "${TERRA_DATA_DIR:-data/research}" >/dev/null && say "Data directory validated (${TERRA_DATA_DIR:-data/research})"

# ---- frontend ------------------------------------------------------------------------
say "Installing web dependencies (npm ci)"
(cd web && npm ci --no-audit --no-fund)
if [ "$TESTS" = 1 ]; then (cd web && npx playwright install chromium); fi
if [ "$MODE" = prod ]; then
  say "Building the web UI"
  (cd web && npm run build)
fi

[ "$START" = 1 ] || { say "Setup complete. Start later with: ./scripts/setup.sh"; exit 0; }

# ---- start ---------------------------------------------------------------------------
port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
port_busy "$API_PORT" && die "Port $API_PORT is already in use. Re-run with API_PORT=<free port>."
port_busy "$WEB_PORT" && die "Port $WEB_PORT is already in use. Re-run with WEB_PORT=<free port>."
say "Starting API on http://127.0.0.1:$API_PORT (docs at /docs)"
TERRA_DATA_DIR="${TERRA_DATA_DIR:-data/research}" TERRA_CORS_ORIGINS="http://localhost:$WEB_PORT" \
  .venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT INT TERM
for _ in $(seq 1 40); do
  curl -fs "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1 && break
  kill -0 "$API_PID" 2>/dev/null || die "API failed to start"
  sleep 0.5
done
say "Starting web UI on http://localhost:$WEB_PORT  (Ctrl+C stops both)"
cd "$ROOT/web"
export PORT="$WEB_PORT" API_URL="http://127.0.0.1:$API_PORT"
if [ "$MODE" = dev ]; then npm run dev; else npm start; fi
