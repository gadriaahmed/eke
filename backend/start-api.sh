#!/usr/bin/env bash
# Starts the kleinanzeigen scraping API on port 8000.
# Run once, leave it in the background while using eke.
#
# One-time setup:
#   cd ~/Workspace/eke/backend/scraper
#   uv sync
#   uv run playwright install chromium

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$SCRIPT_DIR/scraper"

if [ ! -d "$API_DIR" ]; then
  echo "Error: backend/scraper not found at $API_DIR"
  exit 1
fi

# Launch a separate Chrome instance with remote debug port for Immowelt scraping.
# Uses an isolated profile (/tmp/chrome-debug) — your personal Chrome is unaffected.
echo "Starting Chrome with remote debug port 9222..."
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug \
  --no-first-run &
sleep 4

if curl -s http://localhost:9222/json/version | grep -q Browser; then
  echo "Chrome ready."
else
  echo "Warning: Chrome debug port not responding — Immowelt fetch may fail."
fi

cd "$API_DIR"

echo "Starting kleinanzeigen API at http://localhost:8000 ..."

# Resolve uv: prefer a system-wide install, fall back to the project's own
# .venv (where setup installs it via `pip install uv` if Homebrew isn't usable).
if command -v uv >/dev/null 2>&1; then
  UV_BIN="uv"
else
  UV_BIN="$SCRIPT_DIR/../.venv/bin/uv"
  if [ ! -x "$UV_BIN" ]; then
    echo "Error: uv not found on PATH and not found at $UV_BIN"
    echo "Install it with: .venv/bin/pip install uv  (run from the project root)"
    exit 1
  fi
fi

HEADLESS=true "$UV_BIN" run uvicorn main:app --host 0.0.0.0 --port 8000
