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

## M4
- **Use the SDK's resource-server plumbing (`TokenVerifier`, `AuthSettings`, RFC 9728 metadata route) with our own JWT verifier** — the SDK handles the 401 + `WWW-Authenticate: resource_metadata=…` handshake exactly as the MCP authorization spec requires; we only supply validation (PyJWT + JWKS).
- **Scopes checked per tool in `GuardedFastMCP`, not as SDK `required_scopes`** — `required_scopes` applies to every request; we need `db:read` / `sheets:read` / `sheets:write` per tool. The metadata route is replaced so `scopes_supported` lists all three.
- **Asymmetric algorithms only (RS/PS/ES), `exp`/`iss`/`aud` required, 30 s leeway** — blocks `alg=none` and HS256 key-confusion attacks; tolerates small clock skew.
- **Scopes read from `scope`, `scp` and `roles`, with `db.read` accepted for `db:read`** — Entra ID puts delegated scopes in `scp`, app permissions in `roles`, and does not allow `:` in scope values.
- **Stateless Streamable HTTP with JSON responses** — no session affinity needed behind a load balancer; every replica can serve every request (SPEC §4a).
- **Process resources (DB pool, audit file) are tied to the Starlette app lifespan, not FastMCP's `lifespan`** — in stateless mode FastMCP runs its lifespan once per request, which closed the pool after every call (found by the rate-limit test).
- **Per-caller rate limit in memory, per replica** — no Redis to run; with N replicas the effective cap is up to N × limit. For a strict global cap, put Azure API Management / Front Door rate limiting in front (documented in the production profile).
- **DNS-rebinding protection on (Host/Origin allow-list from `PUBLIC_URL` + `HTTP_ALLOWED_HOSTS`)** — cheap defence for servers that end up reachable on a developer laptop.
- **No CORS headers** — clients are MCP hosts calling server-to-server (ChatGPT connectors, Claude) or local tools; no browser front end calls the API. CONVENTIONS' CORS allow-list rule is therefore N/A here.
- **Keycloak 26 in `start-dev` with a committed realm export** — reproducible local IdP with test clients for each scope combination; `--hostname-backchannel-dynamic` lets the server fetch JWKS at `keycloak:8080` while tokens carry `iss=http://localhost:8180/realms/mcp`. Test-only, never for production.
- **Runtime image `python:3.12.x-slim-bookworm` (patch tag pinned, bumped by Dependabot), non-root UID 10001, read-only root filesystem in compose** — small attack surface; no shell access needed at runtime.

## M5
- **Gemini REST API via httpx in `eval/llm.py` over the `google-genai` SDK** — httpx is already installed (MCP SDK dependency); one ~150-line module owns the provider, so swapping to another LLM touches only that file. Tool schemas are passed as `parametersJsonSchema`, so MCP's JSON Schemas need no conversion.
- **Expected answers computed at run time (reference SQL / the demo sheet), not hard-coded** — sample order dates are relative to the seed day, so "last quarter" answers change; computing them keeps every run honest.
- **A fresh server (and fresh in-memory spreadsheet) per task** — write tasks can't leak into later tasks, and each check sees exactly what that task did.
- **Response cache keyed by the full request (`eval/.cache/`, git-ignored) + throttle (GEMINI_RPM, default 8)** — re-runs are free and reproducible on the free tier; only synthetic data is ever sent.
- **python-dotenv (already a pydantic-settings dependency) loads `.env` for `make eval`** — the eval's GEMINI_* variables are not server settings.
- **Latency measured through an in-process MCP client session** — includes JSON-RPC, validation, all safety layers and the Postgres round trip; excludes the network, which depends on the deployment.

## M6
- **PyPI trusted publishing (OIDC) over an API token** — nothing to leak or rotate; PyPI attestations are generated in the same step.
- **Release on signed `vX.Y.Z` tags, with a verify job that checks tag = pyproject = server.json = CHANGELOG** — one source of truth, enforced; `tests/test_packaging.py` catches drift before a tag is ever pushed.
- **Image on GHCR (multi-arch amd64/arm64) with SBOM + provenance, scanned by Trivy before push and in every CI run (fixable HIGH/CRITICAL fail the build)** — free for public repos, next to the code; arm64 covers Apple-silicon laptops and Graviton/Ampere hosts.
- **MCP Registry entry (`server.json`, schema 2025-12-11) with both a PyPI (`uvx`) and an OCI (`docker`) package** — ownership is proven by the `mcp-name:` marker in the README (PyPI) and the `io.modelcontextprotocol.server.name` image label (OCI). Publishing is gated behind the `PUBLISH_MCP_REGISTRY` repo variable because listing is the owner's decision.
- **`mcp-publisher` pinned to v1.8.8, Actions pinned to major versions (checkout v7, setup-uv v10, CodeQL v4, Trivy v0.36.0, docker/* current majors)** — Dependabot (uv, Actions, Docker, Compose, npm) keeps them moving; the publisher is pinned to a release older than two weeks.
- **CodeQL `security-extended` for Python, JS/TS (the site) and the workflows themselves** — free on public repos; workflow injection is a real supply-chain risk.
- **`apt-get upgrade` in the runtime stage** — the pinned `python:3.12.12-slim-bookworm` base shipped fixable HIGH/CRITICAL CVEs in `perl-base` (an Essential package that can't be removed); applying Debian security updates at build time brought Trivy to 0. Dependabot bumps the base tag.

## M7
- **Website reference data generated from the code (`scripts/export_tools.py`) and checked byte-for-byte in `make lint` and CI** — the tools page comes from a real `tools/list` call, configuration from `.env.example`, numbers from `eval/results.json`, the changelog from `CHANGELOG.md`; the docs can't drift.
- **Shiki at build time (server components) for syntax highlighting** — the static site ships no highlighter JavaScript; dual light/dark themes via CSS variables.
- **Next.js 16.4 static export, React 19.3, Tailwind 4.3, TypeScript 6.0** — the newest releases at least two weeks old; TypeScript 7 (native compiler) is skipped until Next's type-check integration supports it.
- **`clsx` + `tailwind-merge` for `cn()` instead of the newer `cn` package the shadcn 4.23 CLI installs** — the long-standing, widely used pair; same behaviour, and components import `cn` from `@/lib/utils` as before.
- **ESLint 10 flat config from `eslint-config-next` directly (no FlatCompat)** — ESLint 9 is end-of-life.
- **Playwright runs against the static export served by a 40-line Node server (`e2e/serve.mjs`)** — tests exactly what gets deployed, with no extra dependency.
- **Security headers (CSP, HSTS, frame-ancestors none…) in `site/vercel.json`** — the static export has no server; `script-src 'unsafe-inline'` is required by Next's inline hydration data and is acceptable for a site with no user input or secrets.
- **Built to `docs/ui/STITCH_PROMPT.md` with shadcn defaults** — the Stitch project is private and was not accessible during the build; aligning with its exports is a tracked follow-up (KICKOFF rule 6).
- **`--env-file` CLI option** — lets the client config reference a 600-permission file instead of embedding `DATABASE_URL` and key paths, matching the site's "never put secrets in the client config" guidance.

## M8
- **Azure Container Apps (consumption) over AKS or App Service** — scale-out of a stateless HTTP container with no cluster to run; managed identity, Key Vault secret references and Log Analytics are built in.
- **User-assigned managed identity + Key Vault references (RBAC: Key Vault Secrets User only)** — the identity exists before the app, so secrets resolve on the first revision; no secret ever appears in app settings, Bicep or the repo.
- **Logs go to Log Analytics with a workspace-based Application Insights** — the server already writes structured JSON (audit lines) to stdout; Container Apps ships it, no SDK needed in the app.
- **Optional VNet integration (`infrastructureSubnetId`)** — the realistic production path to a client's private Postgres; off by default so the template deploys anywhere.
- **Deploy workflow gated by `AZURE_DEPLOY_ENABLED` and using OIDC (`azure/login`)** — validated but never deployed by us (SPEC §4a); no Azure credentials stored in GitHub.
- **Bicep lint in CI fails on any warning (SARIF output checked)** — `bicep lint` alone only fails on errors.
- **Optional Sentry via the `[sentry]` extra, scrubbing exception messages and request data** — error tracking without ever sending SQL text or cell values.
- **`render.yaml` as a self-host example (Render + Neon) rather than a hosted demo** — a public endpoint needs an always-on IdP, which doesn't fit $0 (SPEC §8); the "live demo" is the PyPI package.

## M9
- **Server logs are JSON lines with the request ID in HTTP mode (`LOG_FORMAT=auto`)** — CONVENTIONS §10 asks for structured logs with a request ID on every request; stdio keeps readable text on stderr for local debugging.
- **Usage tracking (CONVENTIONS §10) lives in the audit log, not a database table** — the server owns no tables (SPEC §4a); `duration_ms`, `row_count`, `outcome` and caller per call are queryable in Log Analytics. There are no tokens or LLM cost per call: the server never calls an LLM.
- **Retention:** the server stores no uploads or conversations; audit lines live in Log Analytics with `logRetentionDays` (default 90) in the Bicep profile, or wherever `AUDIT_LOG_PATH` points (rotate with logrotate).
- **Backups / PITR: not applicable** — the server owns no data; the client's Postgres keeps its own backup policy.

## Post-launch
- **`astral-sh/setup-uv` pinned to an exact version (v10.4.0)** — unlike the other actions it publishes no floating major tag, so `@v10` failed on the first GitHub run. Dependabot bumps it.
- **Dependabot ignores major versions (and Python ≥ 3.13 base images)** — SPEC pins the stack; the first push produced majors (MCP SDK 2.x, Python 3.15, Postgres 18, TypeScript 7, sqlglot 30, @types/node 26) that would each need code and doc changes. Majors are upgraded deliberately with a DECISIONS entry; minor/patch updates still arrive grouped.
