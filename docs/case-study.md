# Upwork case study (draft)

**Title:** Safe AI access to company data — an audited MCP server for PostgreSQL and Google Sheets

## Problem
Teams want to ask an AI assistant "what were last month's top customers?" about their own database and
spreadsheets, but won't give it unrestricted credentials: one bad query or prompt injection could change
data, leak tables it shouldn't see, or run up load.

## Solution
An open-source Model Context Protocol server that Claude, ChatGPT and Cursor connect to. It is read-only by
default and layers five independent defences — OAuth scopes, allow-lists, a SQL parser that only lets a
single SELECT through, READ ONLY transactions with timeouts and row caps, and a read-only database role.
Every tool call is written to a JSON audit log. It runs locally over stdio or as a stateless HTTPS service
behind the company's identity provider (Microsoft Entra ID), with a production profile on Azure.

## Stack
Python 3.12 · official MCP SDK (FastMCP) · psycopg 3 · sqlglot · Google Sheets API · Pydantic v2 ·
OAuth 2.1 resource server (JWT/JWKS) · Docker · Azure Container Apps + Key Vault + managed identity +
Application Insights (Bicep) · GitHub Actions (CI, CodeQL, Trivy, trusted publishing) · Next.js + shadcn/ui
docs site. Reasons for each choice: `docs/DECISIONS.md`.

## Result
- 8 tools; **70/70** attack and misuse attempts blocked in the CI safety suite.
- p95 latency under **50 ms** per tool call against the sample database.
- Remote mode verified end to end with a real identity provider (13/13 checks).
- Natural-language task success: *fill in from `eval/results.md` after `make eval` with a Gemini key.*
- Published on PyPI (`uvx mcp-postgres-sheets`) and the MCP Registry: *links after the first release.*
