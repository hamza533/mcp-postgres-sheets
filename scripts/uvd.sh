#!/usr/bin/env sh
# Run any uv command inside Docker, for machines without Python/uv installed.
#   scripts/uvd.sh run pytest -q
# The virtualenv lives in a named volume (Linux wheels never touch the working tree) and the
# container joins the compose network so DATABASE_URL can point at the `db` service.
set -eu
IMAGE="ghcr.io/astral-sh/uv:0.9.30-python3.12-bookworm-slim"
NETWORK="${UVD_NETWORK:-mcp-postgres-sheets_default}"
docker network inspect "$NETWORK" >/dev/null 2>&1 || NETWORK=bridge
TTY=""; [ -t 0 ] && [ -t 1 ] && TTY="-it"
# MSYS_NO_PATHCONV stops Git Bash on Windows from rewriting /work into a Windows path.
MSYS_NO_PATHCONV=1 exec docker run --rm $TTY \
  --network "$NETWORK" \
  -v "$(pwd)":/work -w /work \
  -v mps-venv:/venv -e UV_PROJECT_ENVIRONMENT=/venv \
  -v "${UVD_CACHE_VOLUME:-uvcache}":/root/.cache/uv -e UV_LINK_MODE=copy \
  -e DATABASE_URL -e TEST_DATABASE_URL -e TEST_ADMIN_DATABASE_URL -e GEMINI_API_KEY -e GEMINI_MODEL \
  -e GOOGLE_SERVICE_ACCOUNT_JSON -e ALLOWED_SHEET_IDS -e UV_FROZEN \
  "$IMAGE" uv "$@"
