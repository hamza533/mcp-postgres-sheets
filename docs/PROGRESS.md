# PROGRESS – handoff log

## Status
**Current milestone:** M9 – Final check. All engineering work is done and verified locally; what remains
needs the owner's accounts (GitHub, PyPI, Google Cloud, Gemini, Vercel) or a human at the keyboard
(GIF/video, Stitch). The repo is on GitHub (hamza533/mcp-postgres-sheets) and CI is green on `main`.

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done |
| M1 | Postgres tools + safety | done |
| M2 | Audit log + stdio transport | done — verified with the SDK stdio client and the MCP Inspector (stdio + HTTP); a manual run in Claude Desktop/Cursor is part of recording the GIF |
| M3 | Google Sheets tools | done — memory backend + mocked Google HTTP; a live Google check needs a service account |
| M4 | Remote mode + OAuth | done — `make remote-smoke` 13/13 against real Keycloak |
| M5 | Evaluation | done — safety 73/73, latency max p95 < 50 ms; the 20 NL tasks need `GEMINI_API_KEY` |
| M6 | Packaging + release pipeline | done — wheel/sdist, `uvx` install, server.json valid, Trivy 0 HIGH/CRITICAL; publishing needs GitHub + PyPI |
| M7 | Project website | done — 8 static pages, generated reference, 19/19 Playwright; Stitch design system applied (Quick Start screen matched; other 5 screens not exported yet) |
| M8 | Production profile + docs | done — Bicep builds/lints clean, README, client guides, render.yaml |
| M9 | Final check | done — pushed to GitHub, CI green (all 5 jobs) |

## Next steps for the owner
1. **GitHub:** done — https://github.com/hamza533/mcp-postgres-sheets, CI green. Review the 9 Dependabot PRs it opened on first push (mostly major bumps: MCP SDK 2.x, Python 3.15, Postgres 18, TypeScript 7, sqlglot 30); they were cut before the CI fix, so rebase them before judging their CI.
2. **Stitch designs:** the design system (`docs/ui/DESIGN.md`) and the Quick Start screen are exported and applied to `/site`. Optional: export the other five screens (select each → Export → .zip) into `docs/ui/` for pixel-level checks.
3. **Gemini key:** free key from https://aistudio.google.com/apikey → `GEMINI_API_KEY=` in `.env` → `make eval` (≈20 min, throttled) → put the task-success number in README "Results" and docs/case-study.md.
4. **Google service account:** create one, enable the Sheets API, import `sample_data/sheets/*.csv` into a new sheet (tabs `Leads`, `Targets`, `Notes`), share it with the service-account email, set `GOOGLE_SERVICE_ACCOUNT_JSON` + `ALLOWED_SHEET_IDS`, and try `sheets_read_range` once against real Google.
5. **PyPI + release:** add the pending trusted publisher and the `pypi` environment (RELEASING.md), then tag `v0.1.0` (or bump to `1.0.0` first). Set `PUBLISH_MCP_REGISTRY=true` when ready to be listed; submit to one or two directories.
6. **Vercel:** import the repo with Root Directory `site` (site/README.md).
7. **Demo:** record the GIF (`docs/images/demo.gif`, linked at the top of README) and a 60–90 s video of Claude Desktop and Cursor using the sample database.

## Acceptance criteria (SPEC §8)
- [~] `uvx mcp-postgres-sheets` (stdio) works in Claude Desktop and Cursor using the README config — `uvx` install from the built wheel verified, stdio verified with the SDK client and MCP Inspector; the GUI run + screenshots/GIF are owner steps.
- [x] Remote mode: `docker compose --profile remote up` starts the server + Keycloak; no token → 401; a token without `sheets:write` can't append (`make remote-smoke`, also a CI job).
- [x] With `READ_ONLY=true`, write tools don't appear in `tools/list` (tests + stdio e2e + safety cases).
- [x] Safety suite passes 100 % (73/73) — runs in CI on every push.
- [x] Every tool call produces one audit line (incl. rejected, invalid and unknown-tool calls).
- [ ] Published to PyPI and listed in the MCP Registry — pipeline ready (release.yml, server.json); needs owner accounts.
- [x] Tested with the MCP Inspector, steps documented (docs/inspector.md).
- [x] Production readiness per §4a: idempotent write tools · per-caller rate limit · `/health` + `/ready` · trusted publishing configured · Playwright smoke test · Bicep validates in CI · README "Production deployment" with Entra ID setup, network notes and a monthly cost estimate.
- [~] Website builds as a static export ✓, tools reference generated from `tools/list` and CI fails if stale ✓; matches `docs/ui/` ✓ (design system + Quick Start screen; other screens follow DESIGN.md); deployed on Vercel — owner step.
- [x] `shadcn` in `.mcp.json`; `neon` not added (self-host example not tested on Neon).
- [~] CONVENTIONS §8 — see below.
- [x] AGENTS.md "Gotchas" lists the read-only role, hidden write tools, Keycloak test-only, safety suite at 100 %.
- [~] "Live demo" = the PyPI package + GIF/video — package builds and installs; publishing and recording are owner steps. README explains why there is no hosted endpoint.

## Done checklist (CONVENTIONS §8)
- [~] Every SPEC acceptance criterion passes — the open items above all need owner accounts or recording.
- [x] Production readiness (§10) met or marked N/A with reasons (SPEC §4a, docs/DECISIONS.md M8/M9); Bicep validates (CI job + verified locally with Bicep 0.49.2).
- [x] Handoff: AGENTS.md, CLAUDE.md (`@AGENTS.md`), Makefile targets, this file; a fresh clone runs `make setup` + `make lint` + the full test suite with no tool-specific files (verified in a clean container).
- [x] `docker compose up` works (db by default; `--profile remote` for the full stack).
- [~] Evaluation script runs and its numbers are in the README — safety + latency yes; NL tasks need a Gemini key.
- [x] CI is green — first run on GitHub 2026-11-23 (after pinning setup-uv to v10.4.0 and a Prettier fix).
- [ ] Demo GIF and 60–90 s video — owner.
- [x] Live demo deployed, or the README explains why not — README explains (no always-on IdP at $0) and documents self-hosting (Azure, Render + Neon).
- [x] Upwork case study drafted (docs/case-study.md) — fill in the task-success number after `make eval`.

## Blockers / open questions
- None blocking. The other five Stitch screens are not exported (optional, see step 2).
- Everything else above is an owner step, not a blocker for further engineering.

## How to verify
- `make setup && make check` (or `make check DOCKER=1` without uv) → ruff, mypy, generated-reference check, 254 pytest tests (unit, integration on real Postgres, safety suite 73 cases, MCP protocol, stdio subprocess, HTTP + OAuth).
- `make eval-safety` → `eval/results.md` says 73/73 stopped; `make eval-latency` → p50/p95 table.
- `docker compose --profile remote up -d --wait && make remote-smoke` → ALL PASSED (13 checks).
- `make site-setup site-check site-test` → eslint/prettier/tsc clean, 19 Playwright tests pass.
- `make build && uvx --from dist/*.whl mcp-postgres-sheets --version` → `mcp-postgres-sheets 0.1.0`.
- `az bicep build --file deploy/azure/main.bicep && az bicep lint --file deploy/azure/main.bicep` → clean.
- `AUDIT_LOG_PATH=audit.jsonl uv run mcp-postgres-sheets` + `make inspector` → one JSON line per call.

## Session log
- 2026-11-23 – Claude Code – planned the project: architecture.md, PROGRESS.md.
- 2026-11-23 – Claude Code – M0: uv project, Makefile, CI, compose with seeded Postgres + read-only role.
- 2026-11-23 – Claude Code – M1: sql_guard, db (READ ONLY txn, timeout, cursor row cap), 3 Postgres tools, 56-case safety suite.
- 2026-11-23 – Claude Code – M2: audit log (GuardedFastMCP choke point, redaction), stdio CLI, stdio e2e test.
- 2026-11-23 – Claude Code – M3: Sheets backends (Google + memory), 5 Sheets tools, durable idempotency, 14 more safety cases.
- 2026-11-23 – Claude Code – M4: remote mode (JWT/JWKS verifier, scopes, RFC 9728 metadata, rate limit, health/ready), Dockerfile, Keycloak profile, smoke test, Inspector guide.
- 2026-11-23 – Claude Code – M5: eval harness (safety, 20 Gemini tool-calling tasks with live reference answers, latency), results committed.
- 2026-11-23 – Claude Code – M6: server.json (MCP Registry), release workflow (trusted publishing, GHCR multi-arch, Trivy, SBOM), CodeQL, Dependabot, RELEASING.md.
- 2026-11-23 – Claude Code – M7: /site (Next 16 static export, shadcn/ui), generated tools/config/results/changelog data with CI freshness check, Playwright, Vercel config; --env-file option.
- 2026-11-23 – Claude Code – M8: Azure Bicep profile + CI validation + gated OIDC deploy workflow, README, docs/clients.md, render.yaml, Sentry, case-study draft.
- 2026-11-23 – Claude Code – M9: JSON server logs with request IDs, fresh-clone check, acceptance checklists.
- 2026-11-23 – Claude Code – pushed to GitHub; fixed setup-uv tag (no floating v10) and two Prettier misses; CI green.
- 2026-11-25 – Claude Code – site aligned with the Stitch design system (Inter/JetBrains Mono, grouped docs shell, dark code blocks, callouts, pills); Quick Start matches the exported screen.
