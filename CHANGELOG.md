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
- Audit log: one JSON line per tool call (including rejected, invalid and unknown-tool calls) with
  request ID, caller, tool, redacted arguments, duration, row count and outcome.
- stdio transport: `mcp-postgres-sheets` / `python -m mcp_postgres_sheets` CLI.
- Safety suite: 56 attack and misuse cases (`eval/safety_cases.json`), run in CI.
- Repository foundation: uv project, Makefile, CI, Docker Compose with a seeded synthetic
  e-commerce Postgres database and a read-only role (`deploy/sql/001_readonly_role.sql`).
