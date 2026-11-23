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

## M2
- **Audit, scope checks and rate limiting in one `FastMCP.call_tool` override (`GuardedFastMCP`) over per-tool decorators** — FastMCP validates arguments before a tool function runs, so a decorator would miss invalid-argument and unknown-tool calls; the override sees every call and writes exactly one audit line for each.
- **Redact by default with a SHA-256 fingerprint + length, keeping identifier arguments (schema, table, sheet_id, range…)** — the log stays useful (which table, which sheet, how often the same query repeats) without storing query text or row values that may contain personal data.
- **Audit to stderr in stdio mode, stdout in HTTP mode, or `AUDIT_LOG_PATH`** — stdout is the protocol channel in stdio; in containers stdout is what the platform (Application Insights) collects.
- **A failing audit sink logs an error but does not fail the tool call** — losing a log line is better than an outage caused by a full disk; the error is visible in the server log.
- **MCP Inspector pinned to 2.14.0** — the newest release at least two weeks old.

## M3
- **Durable idempotency via Sheets developer metadata over a server-side store** — the server owns no database tables (SPEC §4a) and must stay stateless. The hashed key is attached as row-level developer metadata to the rows an append wrote; a retry, even on another replica, finds it with one `developerMetadata.search` call. A process-local LRU cache is the fast path. Known gaps: the append and the marker are two API calls (a crash in between can allow one duplicate), and Google caps developer metadata per spreadsheet, so very high-volume append workloads should use a database instead.
- **`sheets_update_range` treats the key as a short-circuit only** — overwriting the same cells with the same values is already idempotent.
- **`valueInputOption=RAW` for every write** — prevents formula injection (`=IMPORTXML(...)`, `=HYPERLINK(...)`) from AI-generated values; the text is stored, never evaluated.
- **In-memory Sheets backend (`SHEETS_BACKEND=memory`) bundled with a synthetic demo spreadsheet** — lets anyone try the Sheets tools in under 5 minutes without a Google Cloud project, and makes the tests/eval deterministic. It is clearly a demo backend; production uses `google`.
- **Tools are only registered when their backend is configured** — `tools/list` shows exactly what works; an AI never picks a tool that can only fail.
- **Google client calls run in worker threads with a fresh `AuthorizedHttp` per attempt** — `google-api-python-client` is synchronous and httplib2 is not thread-safe. Static discovery documents mean no network call at start-up.
- **Retries: exponential backoff with jitter (0.5 s · 2ⁿ, ±50 %, max 30 s), honouring `Retry-After`, on 429/5xx/network errors only** — 4xx other than 429 are caller errors and never retried.
