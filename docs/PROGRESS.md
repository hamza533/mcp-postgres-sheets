# PROGRESS – handoff log

## Status
**Current milestone:** M7 – Project website (next)

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done |
| M1 | Postgres tools + safety | done |
| M2 | Audit log + stdio transport | done — verified with the SDK stdio client; Claude Desktop/Cursor check is a user step |
| M3 | Google Sheets tools | done — tested with the memory backend and mocked Google HTTP; live Google check waits for a service account (user step) |
| M4 | Remote mode + OAuth | done — `make remote-smoke` 13/13 against real Keycloak; Inspector CLI verified (stdio + HTTP) |
| M5 | Evaluation | done — safety 70/70, latency max p95 < 50 ms; 20 NL tasks wait for `GEMINI_API_KEY` (user step) |
| M6 | Packaging + release pipeline | done — wheel/sdist build, `uvx` install verified, server.json validates (schema 2025-12-11), Trivy 0 HIGH/CRITICAL, actionlint clean. Publishing needs the repo on GitHub + PyPI trusted publisher (user step) |
| M7 | Project website | next |
| M8 | Production profile + docs | not started |
| M9 | Final check | not started |

## Blockers / open questions
- **Publishing (user step):** create the GitHub repo `hamza533/mcp-postgres-sheets` and push; add the PyPI pending trusted publisher + `pypi` environment (see RELEASING.md); set `PUBLISH_MCP_REGISTRY=true` when ready to be listed.
- **Gemini API key (user step):** get a free key at https://aistudio.google.com/apikey, put `GEMINI_API_KEY=` in `.env`, run `make eval` (≈20 min on the free tier because of throttling) → task-success numbers in `eval/results.md`.
- **Google service account (user step):** create a service account, enable the Sheets API, share a copy of the template sheet (import `sample_data/sheets/*.csv`) with its email, then set `GOOGLE_SERVICE_ACCOUNT_JSON` and `ALLOWED_SHEET_IDS` in `.env`. Until then Sheets runs on `SHEETS_BACKEND=memory`.
- Claude Desktop / Cursor: config blocks are written (M8); a manual run in each app is part of recording the GIF (user step).
- Stitch designs (`docs/ui/`) not exported yet: the Stitch project needs a Google sign-in (user step).

## How to verify
- `make setup && make check` (or `make check DOCKER=1` without uv) → ruff, mypy and ~225 pytest tests pass,
  including `tests/test_safety_suite.py` (70 cases) against the real sample Postgres.
- `make db` then `psql postgresql://mcp_readonly:mcp_readonly@localhost:5544/shop` → 500 customers,
  1,500 orders; `INSERT` fails with "read-only transaction"; `internal.employees` is "permission denied".
- `docker compose --profile remote up -d --wait && make remote-smoke` → ALL PASSED (see docs/inspector.md).
- `make eval-safety` → `eval/results.md` says 70/70 stopped; `make eval-latency` → p50/p95 table.
- `make build && uvx --from dist/*.whl mcp-postgres-sheets --version` → `mcp-postgres-sheets 0.1.0`.
- `AUDIT_LOG_PATH=audit.jsonl uv run mcp-postgres-sheets` then call a tool from `make inspector` → one JSON line per call.

## Session log
- 2026-11-23 – Claude Code – planned the project: architecture.md, PROGRESS.md.
- 2026-11-23 – Claude Code – M0: uv project, Makefile, CI, compose with seeded Postgres + read-only role.
- 2026-11-23 – Claude Code – M1: sql_guard, db (READ ONLY txn, timeout, cursor row cap), 3 Postgres tools, 56-case safety suite.
- 2026-11-23 – Claude Code – M2: audit log (GuardedFastMCP choke point, redaction), stdio CLI, stdio e2e test.
- 2026-11-23 – Claude Code – M3: Sheets backends (Google + memory), 5 Sheets tools, durable idempotency, 14 more safety cases.
- 2026-11-23 – Claude Code – M4: remote mode (JWT/JWKS verifier, scopes, RFC 9728 metadata, rate limit, health/ready), Dockerfile, Keycloak profile, smoke test, Inspector guide.
- 2026-11-23 – Claude Code – M5: eval harness (safety, 20 Gemini tool-calling tasks with live reference answers, latency), results committed.
- 2026-11-23 – Claude Code – M6: server.json (MCP Registry), release workflow (trusted publishing, GHCR multi-arch, Trivy, SBOM), CodeQL, Dependabot, RELEASING.md.
