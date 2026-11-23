# Kickoff – instructions for the AI coding agent

**Paste this into Claude Code (or any AI coding tool) to start:**
> Read `docs/KICKOFF.md`, then `docs/SPEC.md` and `docs/CONVENTIONS.md`, and build this project milestone by milestone as described in KICKOFF.md.

---

## Your job
Build `mcp-postgres-sheets` exactly as described in `docs/SPEC.md`, following every rule in `docs/CONVENTIONS.md`. The stack is decided. Don't add or swap dependencies without a `docs/DECISIONS.md` entry explaining why.

## How to work
1. **Plan first.** Before writing code, create `docs/architecture.md` (Mermaid diagram plus module layout) and `docs/PROGRESS.md` using the milestone list below. Commit both.
2. **One milestone at a time**, each on its own `feat/<milestone>` branch:
   - Small conventional commits.
   - `make check` passes before every commit.
   - Merge to `main` when the milestone's acceptance items pass.
3. **After every milestone:** update `docs/PROGRESS.md` (status, what's next, how to verify, a session-log line) and `docs/DECISIONS.md` if you made any choices.
4. **Ask the user only when truly blocked.** For example: credentials or accounts are needed, or the spec contradicts itself. Otherwise choose the option that best fits the spec and record it in `DECISIONS.md`.
5. **Never commit secrets.** Use `.env` (git-ignored) and keep `.env.example` complete.
6. **UI work:** match the designs in `docs/ui/`. If that folder has no images yet, build the site with clean shadcn/ui defaults and leave a TODO in `PROGRESS.md` to align with the designs later.

## Milestones
| # | Milestone | Done when |
|---|---|---|
| M0 | **Repo foundation** | `AGENTS.md` (from the CONVENTIONS template, with MCP servers and gotchas), `CLAUDE.md` (`@AGENTS.md`), `Makefile` (setup, dev, test, lint, check, eval, seed), `pyproject.toml` + `uv.lock`, `.python-version`, `.gitignore` (including tool folders), `.env.example`, `docker-compose.yml` (Postgres seeded with the sample e-commerce schema and read-only role), CI workflow (lint, type-check, test), MIT `LICENSE`, `CHANGELOG.md`. `make setup && make check` is green. |
| M1 | **Postgres tools + safety** | `postgres_list_tables`, `postgres_describe_table` and `postgres_query`, with the read-only role, READ ONLY transaction, timeout, row cap, sqlglot SELECT-only check and allow-lists. Safety suite (40+ cases) passes at 100% in CI. |
| M2 | **Audit log + stdio transport** | JSON audit line for every call (with redaction). Works in Claude Desktop and Cursor over stdio, and with the MCP Inspector. |
| M3 | **Google Sheets tools** | The 6 Sheets tools via a service account and allow-list. Write tools are hidden when `READ_ONLY=true` and require `idempotency_key`. Retries with backoff on 429/5xx. |
| M4 | **Remote mode + OAuth** | Streamable HTTP, bearer-token validation (JWKS), scope-to-tool mapping, protected-resource metadata, per-caller rate limit, `/health` and `/ready`. A `docker compose --profile remote` Keycloak setup for testing. |
| M5 | **Evaluation** | `make eval` runs the safety suite, the 20 natural-language tasks (Gemini Flash free tier, throttled and cached) and latency checks, then writes `eval/results.md` and `eval/results.json`. |
| M6 | **Packaging + release pipeline** | PyPI package (`uvx mcp-postgres-sheets`) through GitHub Actions trusted publishing, Docker image, image scan, Dependabot, CodeQL, MCP Registry metadata, SemVer release workflow. |
| M7 | **Project website** | `/site` (Next.js static export + shadcn/ui), matching `docs/ui/`. Tools reference generated from `tools/list` in CI, Playwright smoke test, Vercel deploy instructions. |
| M8 | **Production profile + docs** | `deploy/azure/` Bicep (Container Apps, Entra ID notes, Key Vault, managed identity, Application Insights), validated in CI, with a deploy workflow that's disabled by default. README in the CONVENTIONS template, with results, a production deployment section and a cost estimate. Setup guides for Claude Desktop, Claude Code, Cursor and ChatGPT. |
| M9 | **Final check** | Every acceptance criterion in `SPEC.md` section 8 and the CONVENTIONS section 8 checklist ticked in `PROGRESS.md`. A fresh clone passes `make setup && make check`. |

## What the user does (not the agent)
- Creates the Google Cloud service account and shares a test Sheet with it, then puts the key path in `.env`.
- Gets a Gemini API key for the evaluation.
- Creates the PyPI project and configures trusted publishing, and the Vercel project for `/site`.
- Records the GIF and demo video at the end.
- Submits to the MCP Registry and directories.

When you reach a step that needs one of these, stop, list exactly what's needed, and continue with any other work that isn't blocked.
