# PROGRESS – handoff log

## Status
**Current milestone:** M3 – Google Sheets tools (next)

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done |
| M1 | Postgres tools + safety | done — 56/56 safety cases pass |
| M2 | Audit log + stdio transport | done — verified with the SDK stdio client; Claude Desktop/Cursor check is a user step |
| M3 | Google Sheets tools | next |
| M4 | Remote mode + OAuth | not started |
| M5 | Evaluation | not started |
| M6 | Packaging + release pipeline | not started |
| M7 | Project website | not started |
| M8 | Production profile + docs | not started |
| M9 | Final check | not started |

## Blockers / open questions
- Claude Desktop / Cursor: config blocks are written (M8); a manual run in each app is part of recording the GIF (user step).
- Stitch designs (`docs/ui/`) not exported yet: the Stitch project needs a Google sign-in (user step).

## How to verify
- `make setup && make check` (or `make check DOCKER=1` without uv) → ruff, mypy and ~120 pytest tests pass,
  including `tests/test_safety_suite.py` (56 cases) against the real sample Postgres.
- `make db` then `psql postgresql://mcp_readonly:mcp_readonly@localhost:5544/shop` → 500 customers,
  1,500 orders; `INSERT` fails with "read-only transaction"; `internal.employees` is "permission denied".
- `AUDIT_LOG_PATH=audit.jsonl uv run mcp-postgres-sheets` then call a tool from `make inspector` → one JSON line per call.

## Session log
- 2026-11-23 – Claude Code – planned the project: architecture.md, PROGRESS.md.
- 2026-11-23 – Claude Code – M0: uv project, Makefile, CI, compose with seeded Postgres + read-only role.
- 2026-11-23 – Claude Code – M1: sql_guard, db (READ ONLY txn, timeout, cursor row cap), 3 Postgres tools, 56-case safety suite.
- 2026-11-23 – Claude Code – M2: audit log (GuardedFastMCP choke point, redaction), stdio CLI, stdio e2e test.
