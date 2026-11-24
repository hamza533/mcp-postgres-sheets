# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/). Tool names and input schemas are part of the
public API: breaking changes to them only happen in a major version.

## [Unreleased]

### Added
- Postgres tools: `postgres_list_tables`, `postgres_describe_table`, `postgres_query` with layered
  safety (read-only role, READ ONLY transaction, statement timeout, row cap via server-side
  cursor, sqlglot single-SELECT check, function deny-list, schema/table allow-lists).
- Google Sheets tools: `sheets_list_tabs`, `sheets_read_range`, `sheets_find_rows`, and (only when
  `READ_ONLY=false`) `sheets_append_rows` and `sheets_update_range` with a required `idempotency_key`.
  Service-account auth, `ALLOWED_SHEET_IDS`, timeouts and retries with backoff on 429/5xx.
- In-memory Sheets backend with a synthetic demo spreadsheet (`SHEETS_BACKEND=memory`).
- Production profile: `deploy/azure/main.bicep` (Container Apps, Key Vault, managed identity, Log
  Analytics + Application Insights, Entra ID), validated in CI; disabled-by-default deploy workflow.
- Optional Sentry error tracking (`SENTRY_DSN`, `[sentry]` extra) with scrubbing.
- JSON server logs with request IDs (`LOG_FORMAT`, default JSON in HTTP mode).
- Docs: full README, client setup guides (`docs/clients.md`), `render.yaml` self-host example.
- Project website (`/site`): Next.js static export with shadcn/ui — home, quick start per client,
  configuration, security model, generated tools reference, remote mode, changelog; Playwright smoke tests;
  Vercel deploy config with security headers.
- `--env-file PATH` CLI option to keep secrets out of AI client config files.
- Evaluation (`make eval`): safety suite (73/73 stopped), 20 natural-language tasks run by Gemini Flash
  with tool calling (needs `GEMINI_API_KEY`), latency p50/p95 per tool → `eval/results.{md,json}`.
- Remote mode (`TRANSPORT=http`): stateless Streamable HTTP, OAuth 2.1 bearer-token validation via
  JWKS (any OIDC provider), per-tool scopes `db:read` / `sheets:read` / `sheets:write`, RFC 9728
  protected-resource metadata, per-caller rate limit, `/health` and `/ready`, X-Request-ID.
- `docker compose --profile remote`: server + Keycloak test realm; `make remote-smoke`.
- Packaging: PyPI package (`uvx mcp-postgres-sheets`), multi-arch Docker image on GHCR, MCP Registry
  `server.json`; release workflow with trusted publishing, Trivy scan, SBOM/provenance; CodeQL and
  Dependabot; `RELEASING.md`.
- Dockerfile (non-root, pinned base images).
- Audit log: one JSON line per tool call (including rejected, invalid and unknown-tool calls) with
  request ID, caller, tool, redacted arguments, duration, row count and outcome.
- stdio transport: `mcp-postgres-sheets` / `python -m mcp_postgres_sheets` CLI.
- Safety suite: 73 attack and misuse cases (`eval/safety_cases.json`), run in CI.
- Repository foundation: uv project, Makefile, CI, Docker Compose with a seeded synthetic
  e-commerce Postgres database and a read-only role (`deploy/sql/001_readonly_role.sql`).

### Security
- SQL check: a CTE now only hides a table name inside its own scope (Postgres rules, incl.
  non-recursive forward references), and an unqualified table that is allowed in only some of
  `ALLOWED_SCHEMAS` must be schema-qualified. Both previously let a query read a table outside
  `ALLOWED_TABLES`.
- Google Sheets appends are no longer retried automatically after a timeout or 5xx (the rows may
  already be written); concurrent calls with the same `idempotency_key` write once; a failure to
  store the idempotency marker no longer reports a successful append as failed.
- Remote mode: tokens with an unknown `kid` trigger at most one JWKS refetch per minute.
- Release pipeline: actions pinned to commit SHAs, `mcp-publisher` checksum-verified, pushed
  arm64 image scanned by digest.

### Fixed
- `sheets_read_range` requests at most `max_rows + 1` rows instead of downloading the whole range.
- `postgres_describe_table` folds unquoted names to lower case like Postgres (`Orders` → `orders`).
