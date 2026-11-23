# DECISIONS

Short entries: chose X over Y because Z. Newest last.

## Stack (from SPEC §4)
- **Official MCP Python SDK (FastMCP) over the TypeScript SDK or a hand-rolled protocol layer** — tracks the spec, and same language as the other repos.
- **psycopg 3 + psycopg-pool over asyncpg/SQLAlchemy** — standard driver, native async, server-side parameter handling; no ORM because the server owns no tables.
- **sqlglot over regex** — a real parser reliably tells a single `SELECT` from DML, multi-statements and data-modifying CTEs.
- **google-api-python-client + service account over user OAuth** — official client; no browser flow needed for local use.
- **PyJWT[crypto] for bearer-token validation** — small, maintained, has a JWKS client with key caching; the SDK only defines the `TokenVerifier` interface.

## M0
- **`src/mcp_postgres_sheets/` package over the `/app` folder from CONVENTIONS §3** — this is a library published to PyPI; a top-level package called `app` would clash with other installed packages. The src layout also stops tests from importing the unbuilt working tree by accident.
- **`uv_build` as the build backend over hatchling** — uv already builds and publishes; one tool, no extra build dependency.
- **pydantic-settings for configuration** — already a dependency of the MCP SDK (no new package), and it gives typed, validated env vars with `SecretStr` for secrets.
- **Sample data generated in SQL (`setseed` + `generate_series`) over a Python generator or CSV fixtures** — loads in Postgres' own init step with no extra container, deterministic, ~5.9k rows. Order dates are relative to the seed day so "last quarter" questions always have data.
- **Host port 5544 for the sample Postgres** — 5432/5433 are commonly taken by other local Postgres instances.
- **`scripts/uvd.sh` (uv inside Docker) plus `make … DOCKER=1`** — contributors without Python/uv can still run every target; the virtualenv lives in a Docker volume so Linux wheels never touch the working tree.
- **Extra environment variables beyond SPEC §9**: `HTTP_HOST`, `PUBLIC_URL`, `HTTP_ALLOWED_HOSTS`, `OAUTH_JWKS_URL`, `SHEETS_BACKEND`, `SHEETS_MEMORY_FILE`, `LOG_LEVEL` — each is needed to run in a container, behind a proxy, or without a Google account; all have safe defaults.
- **`TRANSPORT=http` refuses to start without OAuth settings** — an unauthenticated HTTP endpoint to a database is too easy to expose by accident; the spec only describes HTTP mode with OAuth.
