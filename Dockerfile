# syntax=docker/dockerfile:1.7
# mcp-postgres-sheets — small, non-root runtime image. Pinned base images (Dependabot bumps them).
#   docker build -t mcp-postgres-sheets .
#   docker run --rm -i -e DATABASE_URL=... mcp-postgres-sheets                 # stdio
#   docker run --rm -p 8765:8765 -e TRANSPORT=http -e OAUTH_ISSUER=... ...     # remote mode

FROM ghcr.io/astral-sh/uv:0.9.30-python3.12-bookworm-slim AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-editable
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.15.2-slim-bookworm AS runtime
LABEL org.opencontainers.image.title="mcp-postgres-sheets" \
      org.opencontainers.image.description="MCP server for PostgreSQL and Google Sheets: read-only by default, audited." \
      org.opencontainers.image.source="https://github.com/hamza533/mcp-postgres-sheets" \
      org.opencontainers.image.licenses="MIT" \
      io.modelcontextprotocol.server.name="io.github.hamza533/mcp-postgres-sheets"
# Pick up Debian security fixes released after the base image was built (Trivy gates on these).
RUN apt-get update \
 && apt-get -y upgrade --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 mcp \
 && useradd --system --uid 10001 --gid mcp --home-dir /app --shell /usr/sbin/nologin mcp
COPY --from=build --chown=mcp:mcp /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HTTP_HOST=0.0.0.0 \
    HTTP_PORT=8765
WORKDIR /app
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0) if os.environ.get('TRANSPORT','stdio')!='http' else urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('HTTP_PORT','8765')}/health\", timeout=3)"]
ENTRYPOINT ["mcp-postgres-sheets"]
