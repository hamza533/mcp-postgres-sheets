#!/usr/bin/env sh
# Run a command in Node 22 inside Docker, in site/, for machines without Node installed.
#   scripts/noded.sh npm ci
#   NODED_PORT=3301 scripts/noded.sh npm run dev -- -H 0.0.0.0      # publish the dev server
# node_modules lives in a named volume (Linux binaries never touch the working tree).
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TTY=""; [ -t 0 ] && [ -t 1 ] && TTY="-it"
PORTS=""; [ -n "${NODED_PORT:-}" ] && PORTS="-p ${NODED_PORT}:3000"
# shellcheck disable=SC2086  # $TTY and $PORTS are intentionally word-split (or empty)
MSYS_NO_PATHCONV=1 exec docker run --rm $TTY $PORTS \
  -v "$ROOT":/repo -w /repo/site \
  -v mps-site-node-modules:/repo/site/node_modules \
  -v mps-npm-cache:/root/.npm \
  -e npm_config_update_notifier=false -e NEXT_TELEMETRY_DISABLED=1 -e CI \
  "${NODED_IMAGE:-node:22-bookworm}" "$@"
