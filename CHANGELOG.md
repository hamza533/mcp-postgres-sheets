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
- Evaluation (`make eval`): safety suite (70/70 stopped), 20 natural-language tasks run by Gemini Flash
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
- Safety suite: 70 attack and misuse cases (`eval/safety_cases.json`), run in CI.
- Repository foundation: uv project, Makefile, CI, Docker Compose with a seeded synthetic
  e-commerce Postgres database and a read-only role (`deploy/sql/001_readonly_role.sql`).
