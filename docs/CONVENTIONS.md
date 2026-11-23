# Shared Conventions – AI Portfolio Repos

Copy this file into every repo as `docs/CONVENTIONS.md`, and the project's spec as `docs/SPEC.md`. Each project's `SPEC.md` overrides it only where it says so explicitly.

## 1. Guiding principle
**Every component must have a one-sentence reason a client would accept.** If plain code does the job in under about 50 lines, don't add a framework. Don't add a tool just to show it was used. When the build agent wants to add a dependency that isn't listed in the spec, it records the reason in `docs/DECISIONS.md` first.

## 2. Defaults (all Python repos)
| Area | Default | Reason |
|---|---|---|
| Language | Python 3.12 | One language across the Python repos; the most common language for AI work. |
| Package manager | `uv` with `pyproject.toml` + lockfile | Fast, reproducible installs; one file for dependencies and tool config. |
| API | FastAPI + Pydantic v2 | Typed validation and automatic OpenAPI docs that clients can try out. |
| Database | PostgreSQL 16 (+ `pgvector` only when vector search is needed) | One database to run, back up and explain. |
| LLM | Google Gemini Flash (free tier); model name set in `.env` | $0 development. Structured JSON output. Swapping to OpenAI or Azure OpenAI for a client only changes `app/llm.py`. |
| Embeddings | Gemini embedding model (free tier) | Same provider and key as the LLM. |
| Front end (when a project has one) | Next.js + TypeScript + **shadcn/ui** + Tailwind CSS | Accessible ready-made components whose code is copied into the repo, so nothing is locked in. Tailwind matches design-tool exports. Same setup across every repo. |
| Lint/format | `ruff` (Python), ESLint + Prettier (front end) | Standard tools for each language. |
| Tests | `pytest` (unit + integration against real Postgres); Playwright for end-to-end UI tests | Standard tools. End-to-end tests prove the main user flow works. |
| Migrations | Alembic | Versioned, repeatable schema changes, required for production. |
| Type checking | mypy (Python), tsc (TypeScript) | Catches errors before runtime and makes handoffs between tools safer. |
| Containers | Docker + `docker compose` | One-command setup for reviewers and clients. |
| CI | GitHub Actions: lint, test, build image | Free for public repos; shows each change is checked. |
| License | MIT | Clients can reuse the code freely. |

Call the LLM through one small internal module (`app/llm.py`), not a third-party abstraction layer. If a client wants a different provider, only that module changes.

## 3. Repo layout (Python)
```
AGENTS.md       instructions for ANY AI coding tool (single source of truth)
CLAUDE.md       one line: @AGENTS.md  (makes Claude Code load AGENTS.md)
Makefile        standard commands every tool and human uses
/app            application code
/tests          unit + integration tests
/eval           evaluation scripts, test sets, results (committed)
/sample_data    small, license-safe sample inputs
/docs           SPEC.md, CONVENTIONS.md, PROGRESS.md, DECISIONS.md, architecture.md, images/
docker-compose.yml
.env.example    every variable, with a comment and a safe placeholder
.python-version / .nvmrc   pinned runtime versions
uv.lock / package-lock.json   committed lockfiles
README.md
LICENSE
```

## 3a. AI-tool handoff (every repo)
Goal: a fresh session in any tool or account can clone the repo and continue the work with no chat history, using only what's in git.

**Rules**
1. **All project knowledge lives in the repo, never only in a tool's memory or chat.** The spec, decisions, progress and design docs are plain Markdown under `/docs`. If the build agent (for example the AI-DLC plugin) writes a design doc, it is committed to `docs/` too.
2. **`AGENTS.md` is the single instruction file.** It's read natively by Codex, Cursor, Copilot, Antigravity and others.
   - `CLAUDE.md` contains only `@AGENTS.md`, so Claude Code loads the same rules.
   - No `.cursorrules`, `GEMINI.md`, `.github/copilot-instructions.md` or other per-tool rule files. One file means nothing goes out of date.
3. **Tool-specific folders are not committed:** `.claude/`, `.cursor/`, `.codex/`, `.gemini/`, `.agent/`, `.vscode/` and `.idea/` are in `.gitignore`.
   **MCP servers (development helpers):**
   - Add only the servers a project actually needs.
   - Commit them in `.mcp.json` (Claude Code project scope). It never contains secrets: use `${VAR}` placeholders.
   - `AGENTS.md` has an "MCP servers" section: each server, why it's used, and the one-line setup for Claude Code, Cursor, Codex and Antigravity. Each developer runs that setup in their own tool.
   - Defaults:
     - `shadcn` (`npx shadcn@latest mcp`) for projects with a Next.js UI.
     - `neon` (`https://mcp.neon.tech/mcp`, preferably `?readonly=true`), added only at the deployment step.
   - Nothing else is added without a `DECISIONS.md` entry.
4. **The same commands work everywhere** through the `Makefile`:
   - `make setup` installs dependencies.
   - `make dev` starts everything with `docker compose up`.
   - `make test` and `make lint`; `make check` runs both and must pass before every commit.
   - `make eval` runs the evaluation, `make seed` loads the sample data.
5. **`docs/PROGRESS.md` is the handoff log.** Every session ends by updating it, so the next session, in any tool, knows where to start:
   - **Status:** current milestone, done, in progress, next.
   - **Blockers / open questions.**
   - **How to verify:** the commands to run and what you should see.
   - **Session log:** one line per session, in the form `date – tool – what changed`.
6. **Git workflow:**
   - `main` is always green.
   - Work happens on short branches named `feat/…` or `fix/…`, using small conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
   - Merge through a pull request with CI passing.
   - Never leave uncommitted work at the end of a session: commit with a `wip:` prefix on the branch if it isn't finished.
7. **Pinned versions:** runtimes (`.python-version`, `.nvmrc`), lockfiles, and Docker image tags. The same repo should behave the same in every tool.
8. **Secrets only in `.env`.** Never commit them. `.env.example` lists every variable, and tools must not write keys into code or into docs.

**`AGENTS.md` template**
```markdown
# AGENTS.md
## Project
<one-line value statement>. Full requirements: docs/SPEC.md. Shared rules: docs/CONVENTIONS.md.
## Start here
1. Read docs/PROGRESS.md (current status + next step).
2. Read docs/SPEC.md and docs/DECISIONS.md before changing the stack.
## Commands
make setup | make dev | make test | make lint | make check | make eval | make seed
## Structure
<short folder map>
## Rules
- Follow docs/SPEC.md stack; adding a dependency requires a DECISIONS.md entry.
- `make check` must pass before committing; never commit secrets.
- Small conventional commits on a feat/ or fix/ branch.
- End every session by updating docs/PROGRESS.md (status, next step, session log line).
## MCP servers
| Server | Why | Claude Code | Cursor / Codex / Antigravity |
|---|---|---|---|
| shadcn | install/browse UI components | in .mcp.json | `pnpm dlx shadcn@latest mcp init --client cursor` (or `codex`); Antigravity: add `npx shadcn@latest mcp` in its MCP settings |
| neon (deploy step only) | manage the demo DB | `claude mcp add --transport http neon https://mcp.neon.tech/mcp` then `/mcp` to log in | add URL `https://mcp.neon.tech/mcp` in the tool's MCP settings |
## Gotchas
<project-specific pitfalls, e.g. Gemini free-tier rate limits, Azure DI 2-page free-tier limit>
```

## 4. Every repo must ship
1. **README** (template in section 7): demo GIF first, then a one-line value statement.
2. **Architecture diagram** as Mermaid in `docs/architecture.md`, also embedded in the README.
3. **One-command run:** `docker compose up` works on a clean machine with only `.env` filled in.
4. **`.env.example`** listing every required key, with links to where each key is obtained.
5. **Sample data** that lets someone see a result within 5 minutes.
6. **Evaluation / Results** section with real numbers produced by a committed script (`make eval` or `uv run python -m eval.run`). Commit the results file too.
7. **Demo mode** (`DEMO_MODE=true`): rate limit per IP, a per-day cost cap, pre-loaded sample data, and destructive actions disabled. Public demos run in this mode.
8. **Tests** for core logic, run in CI.
9. **MIT license.**
10. **`docs/DECISIONS.md`**: short entries of the form "chose X over Y because Z". This becomes the "Stack" part of the Upwork case study.

## 5. Security & secrets
- Secrets only come from environment variables. Never commit `.env`.
- Logs never contain secrets, full documents or personal data. Log IDs and metadata only.
- Sample data must be synthetic or from a public dataset with a compatible license. Never use real client data.

## 6. Cost rules (development)
- Use the smallest model that passes the evaluation. Each repo logs token usage per request.
- Each repo states its expected development cost in the README.
- Stay on free tiers wherever they cover development, and note the limits in the README.

## 7. README template
```
# <Project name>
<demo GIF>
**<One-line value statement: who it's for + what it does + result>**

[Live demo] · [2-min video] · [Architecture]

## What it does
## Results            <- table with real numbers from /eval
## Architecture       <- Mermaid diagram
## Stack & why        <- one line per component (from DECISIONS.md)
## Quick start        <- docker compose up, in 3 steps or fewer
## Configuration      <- points to .env.example
## Evaluation         <- how to reproduce the numbers
## Costs              <- dev cost + cost per unit (per doc / per chat / per call)
## Production deployment <- Azure architecture, monthly cost estimate, scaling, security summary
## Limitations & next steps
## License
```

## 8. Done = all of these
- [ ] Every acceptance criterion in `SPEC.md` passes.
- [ ] Production readiness (section 10): every item is met or explicitly marked not applicable in `SPEC.md`. `deploy/azure/` Bicep validates in CI.
- [ ] Handoff check: `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`), `Makefile` targets and an up-to-date `docs/PROGRESS.md` are in place. A fresh clone runs `make setup && make check` green without any tool-specific files.
- [ ] `docker compose up` works on a clean machine.
- [ ] Evaluation script runs, and its numbers are in the README.
- [ ] CI is green.
- [ ] Demo GIF and a 60–90 second video are recorded.
- [ ] Live demo is deployed in demo mode, or the README explains why not.
- [ ] Upwork case study drafted (Problem → Solution → Stack → Result), using the README numbers.

## 9. Development and hosting
- **During development:** everything runs locally with `docker compose`. Nothing is deployed until the project is finished.
- **Live demo (at the end):**
  - **Vercel** (Hobby) for Next.js front ends.
  - **Render** (free web service, Docker) for Python backends.
  - **Neon** (free plan, one project per repo) for Postgres, with pgvector where needed.
- **Required in every deployed app:**
  - A `render.yaml`.
  - CORS restricted to the Vercel domain.
  - A `/health` endpoint.
  - A "waking up the demo server" message in the UI, because Render's free plan sleeps when idle.
  - A seed script that rebuilds the demo data.
- **Free-tier rules:**
  - Gemini free-tier data may be used by Google to improve its products, so only synthetic or public sample data goes through it, never client data.
  - Vercel Hobby is for personal, non-commercial use, so client deployments go on the client's own plan.
- Don't take on a paid commitment without approval.

## 10. Production readiness (applies to every project)
The design and code are production-grade, while the demo only runs on free tiers. Every item below is required unless a project's `SPEC.md` says why it doesn't apply.

**Architecture**
- **Stateless API containers:** no local state in production. Files go to object storage, sessions to the database. The API can scale out horizontally.
- **Durable background jobs:** a Postgres-backed job queue, using a `jobs` table and a worker that claims jobs with `SELECT … FOR UPDATE SKIP LOCKED`. Jobs have retries with backoff, a dead-letter status and an idempotency key.
  - This adds no Redis or broker to run.
  - `WORKER_MODE=separate` runs a dedicated worker container, for production.
  - `WORKER_MODE=embedded` runs the worker inside the API process, for the free demo host, which has no background workers.
  - FastAPI `BackgroundTasks` alone is not used for important work.
- **External calls** (LLM, OCR, Sheets, webhooks) have timeouts, retries with backoff and jitter, and idempotency keys where the receiver may see a call twice.
- **Graceful shutdown:** in-flight jobs finish or are released back to the queue.

**Data**
- **Migrations** with Alembic, run automatically on deploy. The app never creates tables at runtime.
- **Retention:** every table holding uploads, conversations or personal data has a documented retention period and a purge job.
- **Backups / point-in-time restore** are documented for the production profile.

**Security**
- **Real authentication:**
  - A `users` table with Argon2-hashed passwords, httpOnly + Secure + SameSite session cookies, CSRF protection on state-changing requests, and login rate limiting.
  - Roles: at least `admin` plus one operational role.
  - The first admin is created with `make create-admin`. No credentials live in `.env`.
- **Input safety:**
  - Strict Pydantic validation.
  - Uploads checked by real file type (magic bytes) and size, and parsed safely.
  - Output encoding in the UI.
- **Security headers:** HTTPS only, CORS allow-list, CSP and the standard security headers on the front end.
- **Secrets:** environment variables in demo, a managed secret store (Azure Key Vault) in production.
- **Containers:** run as non-root, with pinned base images.
- **Supply chain:** GitHub Dependabot and CodeQL enabled (free for public repos), and a container image scan in CI.

**Observability**
- **Structured JSON logs** with a request ID on every request and job. No secrets or personal data in logs.
- **Health checks:** `/health` (liveness) and `/ready` (database and dependencies reachable).
- **Error tracking:** an optional Sentry DSN through an environment variable (free tier). Off unless set.
- **Usage tracking:** key per-request numbers (latency, tokens, cost estimate) recorded in the database, and shown in the admin UI where relevant.

**Quality**
- **Tests:**
  - Unit tests.
  - Integration tests against a real Postgres (the `docker compose` service in CI).
  - End-to-end tests of the main user flow with **Playwright**, for projects with a UI.
- **CI:** lint, type-check (mypy for Python, tsc for TypeScript), tests, Playwright, image build and scan, and Bicep validation.
- **Versioning:** semantic versions with a `CHANGELOG.md`. Images are tagged by version.

**Production profile (documented, validated in CI, not deployed by us)**
- **Target cloud:** Azure, the most common choice among business clients.
  - Azure Container Apps (API + worker).
  - Azure Database for PostgreSQL Flexible Server.
  - Blob Storage.
  - Key Vault.
  - Managed identity, with no secrets in app settings.
  - Application Insights, which collects the JSON logs.
- **Infrastructure as code** in `deploy/azure/` using **Bicep**. CI runs `az bicep build` and lint on it, plus a GitHub Actions deploy workflow that runs on a release tag but is **disabled by default**.
- **Paid tiers in production:**
  - LLM: paid Gemini API or Vertex AI. The free tier is for development and demos only, because free-tier data may be used by Google.
  - Front end: the client's own Vercel plan or Azure.
- **README "Production deployment" section:** the architecture diagram, an estimated monthly cost at a stated volume, scaling notes and a security summary.
