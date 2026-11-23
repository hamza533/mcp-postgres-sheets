# PROGRESS – handoff log

## Status
**Current milestone:** M2 – Audit log + stdio transport (next)

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done |
| M1 | Postgres tools + safety | done — 56/56 safety cases pass |
| M2 | Audit log + stdio transport | next |
| M3 | Google Sheets tools | not started |
| M4 | Remote mode + OAuth | not started |
| M5 | Evaluation | not started |
| M6 | Packaging + release pipeline | not started |
| M7 | Project website | not started |
| M8 | Production profile + docs | not started |
| M9 | Final check | not started |

## Blockers / open questions
- Stitch designs (`docs/ui/`) not exported yet: the Stitch project needs a Google sign-in (user step).

## How to verify
- `make setup && make check` (or `make check DOCKER=1` without uv) → ruff, mypy and ~120 pytest tests pass,
  including `tests/test_safety_suite.py` (56 cases) against the real sample Postgres.
- `make db` then `psql postgresql://mcp_readonly:mcp_readonly@localhost:5544/shop` → 500 customers,
  1,500 orders; `INSERT` fails with "read-only transaction"; `internal.employees` is "permission denied".

## Session log
- 2026-11-23 – Claude Code – planned the project: architecture.md, PROGRESS.md.
- 2026-11-23 – Claude Code – M0: uv project, Makefile, CI, compose with seeded Postgres + read-only role.
- 2026-11-23 – Claude Code – M1: sql_guard, db (READ ONLY txn, timeout, cursor row cap), 3 Postgres tools, 56-case safety suite.
