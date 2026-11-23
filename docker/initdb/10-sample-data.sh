#!/usr/bin/env bash
# Runs once, when the Postgres container starts with an empty data directory.
# 1) synthetic e-commerce schema + data, 2) the read-only role the MCP server connects as.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sample_data/schema.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sample_data/seed.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v ro_user="${MCP_READONLY_USER:-mcp_readonly}" \
  -v ro_password="${MCP_READONLY_PASSWORD:-mcp_readonly}" \
  -v schema=public \
  -f /deploy/sql/001_readonly_role.sql

echo "sample data loaded; read-only role ${MCP_READONLY_USER:-mcp_readonly} created"
