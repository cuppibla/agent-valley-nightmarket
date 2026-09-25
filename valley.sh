#!/usr/bin/env bash
# Open the Night Market: ONE process on ONE port. Ctrl+C closes it.
#
#   bash valley.sh              → http://localhost:3450
#   PORT=3451 bash valley.sh    → somewhere else
#
# The page (site/) is a Next.js app exported to static files once, here, and
# served by the same Python process that owns the line, the editor and the
# workbench. One origin: the browser asks for the mic once, and wss just works.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-3450}"

if [ ! -f .env ]; then
  echo "No .env yet. Run:  cp .env.example .env"
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "No .venv yet. Run:  uv sync"
  exit 1
fi
if ! .venv/bin/python -c "import forge,sys; sys.exit(0 if forge.MODE else 1)" 2>/dev/null; then
  echo "Not configured yet. Either point gcloud at a project (Vertex, the default):"
  echo "    gcloud config set project YOUR_PROJECT_ID"
  echo "or put an API key in .env — see .env.example."
  exit 1
fi

# Build the page once — and again only when something under site/ changed
# after the last build. Learners never run npm by hand.
needs_build=0
if [ ! -f site/out/index.html ]; then
  needs_build=1
elif [ -n "$(find site/app site/components site/lib site/public site/package.json -newer site/out/index.html -print -quit 2>/dev/null)" ]; then
  needs_build=1
fi
if [ "$needs_build" = 1 ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found. The page (site/) is a Next.js app and needs Node 20+:"
    echo "    https://nodejs.org/en/download"
    exit 1
  fi
  if [ ! -x site/node_modules/.bin/next ]; then
    echo "  installing the page's packages (site/) — about a minute, once…"
    (cd site && if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi)
  fi
  echo "  building the page (site/) — about a minute…"
  (cd site && npm run build >/dev/null)
fi

echo
echo "  the Night Market → http://localhost:${PORT}"
echo "  the workbench    → http://localhost:${PORT}/workbench/dev-ui/?app=stage"
echo
exec .venv/bin/uvicorn stage.service:app --host 0.0.0.0 --port "$PORT" --log-level warning
