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

## M1
- **Server-side cursor (`DECLARE … CURSOR` + `FETCH max_rows+1`) over `LIMIT` rewriting or fetching everything** — the row cap holds without rewriting the user's SQL, a million-row result never crosses the wire, and `DECLARE` only accepts a query, which adds another protocol-level layer (it also refuses multiple commands).
- **Execute the original SQL text, not sqlglot's regenerated SQL** — regeneration can subtly change semantics (dialect transpilation); parser differentials are covered by the cursor protocol, the READ ONLY transaction and the role.
- **Function deny-list (`pg_*`, `lo_*`, `dblink*`, `*_to_xml*`, `set_config`, `current_setting`, sequence functions…) over an allow-list** — an allow-list of "safe" functions would reject most real analytics SQL (date_trunc, to_char, window functions); the deny-list targets the functions that sleep, read files, reach other servers, run nested SQL or change settings.
- **Reject unqualified `pg_*` table names** — Postgres resolves them to `pg_catalog` before any allowed schema, so they would otherwise bypass the schema allow-list.
- **`SET LOCAL search_path` to the allowed schemas in every transaction** — unqualified names resolve only inside the allow-list.
- **Postgres error primary message is returned to the AI (with SQLSTATE), never the raw exception** — the AI needs `column "x" does not exist` to correct its query; connection errors become a generic "database not reachable" message.
- **Safety suite as data (`eval/safety_cases.json`) run through a real MCP client session** — the same cases drive CI (`tests/test_safety_suite.py`) and `make eval`, and they test what the AI actually sees, not internal functions.
- **Structured output (Pydantic result models) for every tool** — clients get an `outputSchema` and typed `structuredContent`, plus the JSON text for older clients.
