# AGENTS.md

## Project
Let your AI assistant answer questions from your database and spreadsheets, safely, with read-only defaults and a full audit log. An MCP server (Python, official MCP SDK) for PostgreSQL and Google Sheets. Full requirements: docs/SPEC.md. Shared rules: docs/CONVENTIONS.md.

## Start here
1. Read docs/PROGRESS.md (current status + next step).
2. Read docs/SPEC.md and docs/DECISIONS.md before changing the stack.
3. docs/architecture.md has the module map and the safety layers.

## Commands
make setup | make dev | make test | make lint | make check | make eval | make seed

- No `uv` on the machine? Append `DOCKER=1` (e.g. `make check DOCKER=1`) or call `scripts/uvd.sh <uv args>` directly.
- `make db` starts only the sample Postgres (localhost:5544, db `shop`, role `mcp_readonly`).
- `make eval-safety` runs the safety suite without an API key. `make inspector` opens the MCP Inspector.
- Website: `make site-setup site-check site-test` (Node 22, see site/.nvmrc). No Node? `scripts/noded.sh <cmd>` runs it in Docker (Playwright: `NODED_IMAGE=mcr.microsoft.com/playwright:v1.65.1-noble`).
- `make tools-json` regenerates `site/src/data/` after changing tools, `.env.example`, eval results or CHANGELOG.md — `make lint` fails until you do.

## Structure
```
src/mcp_postgres_sheets/   server code (config, sql_guard, db, sheets, audit, auth, ratelimit, tools/)
tests/                     unit, integration (real Postgres), safety suite, MCP protocol tests
eval/                      safety cases, NL task set, latency benchmark, results.{md,json}
sample_data/               synthetic e-commerce schema + seed, demo spreadsheet for the memory backend
deploy/sql/                read-only role SQL       deploy/keycloak/  realm for the remote test profile
deploy/azure/              Bicep production profile (validated in CI, not deployed)
docker/                    Postgres init script     scripts/  helpers (uvd.sh, export_tools, remote_smoke)
site/                      Next.js static website; tools reference generated from tools/list
docs/                      SPEC, CONVENTIONS, PROGRESS, DECISIONS, architecture, ui/ designs
```

## Rules
- Follow docs/SPEC.md stack; adding a dependency requires a DECISIONS.md entry.
- `make check` must pass before committing; never commit secrets.
- Small conventional commits on a feat/ or fix/ branch.
- End every session by updating docs/PROGRESS.md (status, next step, session log line).
- Tool names and input schemas are a public API: breaking changes only in a major version (update CHANGELOG.md).
- Error messages returned to the AI must never contain connection strings, stack traces or raw driver errors.

## MCP servers
| Server | Why | Claude Code | Cursor / Codex / Antigravity |
|---|---|---|---|
| shadcn | install/browse UI components for `site/` | in .mcp.json | `pnpm dlx shadcn@latest mcp init --client cursor` (or `codex`); Antigravity: add `npx shadcn@latest mcp` in its MCP settings |

`neon` is deliberately not configured: the README's self-host example has not been tested on Neon (see SPEC §8).

## Gotchas
- **The read-only database role is the main safety guarantee.** sqlglot checks, READ ONLY transactions and allow-lists are extra layers; never connect with an owner/superuser role, and never "fix" a failing query by widening grants.
- **Write tools are hidden when `READ_ONLY=true`** — they are not registered, so they don't appear in `tools/list`. Don't add them back conditionally at call time.
- **The safety suite must stay at 100%.** CI fails on any regression. Add a case to `eval/safety_cases.json` for every new attack you think of.
- **The Keycloak profile is for local testing only** (`docker compose --profile remote`): dev-mode Keycloak, throwaway secrets. Production uses the client's IdP (Entra ID).
- **stdio mode: never print to stdout** — stdout is the MCP protocol channel. Logs and audit lines go to stderr or `AUDIT_LOG_PATH`.
- `TRANSPORT=http` refuses to start without `OAUTH_ISSUER` + `OAUTH_AUDIENCE`.
- Keycloak tokens carry `iss=http://localhost:8180/realms/mcp`; inside compose the server fetches JWKS from `http://keycloak:8080` via `OAUTH_JWKS_URL`.
- Gemini free tier (eval only) is rate-limited: the eval throttles and caches responses in `eval/.cache/`. Only synthetic data goes through it.
- `site/src/data/` is generated: never edit it by hand (Prettier ignores it; CI compares it byte-for-byte).
- shadcn 4.x `CommandDialog` does not wrap its children in `<Command>` — do it yourself or cmdk crashes on open.
- Windows + Git Bash: `scripts/uvd.sh` sets `MSYS_NO_PATHCONV=1`; keep LF line endings (`.gitattributes`) or the Postgres init script breaks.
