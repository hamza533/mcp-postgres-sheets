# Google Stitch prompt – project website

Paste everything inside the code block into Stitch and choose **Web**. Export each screen as a PNG at 1920×1080, plus HTML/code if Stitch offers it. Save them here in `docs/ui/` as:

`01-home.png`, `02-quick-start.png`, `03-security.png`, `04-tools.png`, `05-configuration.png`, `06-changelog.png`

```
Design a responsive developer website (browser-based, designed for laptop/desktop screens first at 1440px wide, also works on mobile) for an open-source project called "PG Sheets MCP" — a Model Context Protocol (MCP) server that lets AI assistants safely query a PostgreSQL database and read/write Google Sheets. It is read-only by default, with scoped permissions and a full audit log. Create 6 screens using ONE consistent design system. Use realistic content (no lorem ipsum). Do not draw or imitate the user interface of any real AI product; show AI assistants only as generic, unbranded chat panels.

GLOBAL STYLE
Modern developer-docs style: crisp, technical, trustworthy. Support light and dark themes (show light, include a theme toggle in the header). Neutral slate grays with one emerald accent color; red only for "blocked" examples. Use shadcn/ui-style components (Tailwind CSS): cards, tabs, badges, tables, alerts, code blocks with a copy button and syntax highlighting, a command palette search box. Monospace font for code. Header: logo wordmark "PG Sheets MCP", nav links (Docs, Tools, Security, Changelog), a version badge "v1.0.0", a GitHub stars button, and a search box. Docs pages use a left sidebar (Getting started, Quick start, Configuration, Security model, Tools reference, Remote mode & OAuth, Changelog) and a right "On this page" table of contents. Generous spacing, readable 15px body text, accessible contrast.

SCREEN 1 — HOME (landing page)
Hero: headline "Let your AI assistant query your data — safely", subline "An open-source MCP server for PostgreSQL and Google Sheets. Read-only by default, scoped permissions, full audit log." Primary button "Get started", secondary "View on GitHub". A one-line install code block with copy button: uvx mcp-postgres-sheets. Right side: a generic unbranded chat panel where a user asks "Who were our top 5 customers by revenue last quarter?" and the assistant shows a collapsed tool call chip "postgres_query · 42 ms · 5 rows" followed by a short answer table. Below the hero: a 4-card feature grid (Read-only by default, Layered SQL safety, OAuth scopes for remote use, Audit every call). A "Blocked by design" strip showing an example: DROP TABLE customers; → red badge "Rejected: only a single SELECT is allowed". A "Works with" row of plain text labels (Claude Desktop, Claude Code, Cursor, ChatGPT) — text only, no logos. Results strip: "40/40 misuse attempts blocked", "8 tools", "p95 < 150 ms". Footer with MIT license note, GitHub, PyPI links.

SCREEN 2 — QUICK START
Docs layout. Steps with numbered headings: 1) Create a read-only database role (SQL code block), 2) Share your Google Sheet with the service account (short instruction + alert box), 3) Add the server to your AI client — tabs for "Claude Desktop", "Claude Code", "Cursor", "ChatGPT (remote)", each tab showing the config JSON or command in a code block with copy button, 4) Try it — example prompts list. Success alert at the end: "You're connected — ask a question about your data."

SCREEN 3 — SECURITY MODEL
Docs layout. A layered diagram (5 stacked horizontal layers, top to bottom): OAuth scopes (remote only) → Allow-lists (schemas, tables, sheets) → SQL check (single SELECT only) → Read-only transaction (timeout + row limit) → Read-only database role. Each layer has a one-line explanation. Below: a table "What is blocked" with columns Attempt, Example, Result (DROP/UPDATE, multiple statements, pg_sleep, huge result sets, write tools in read-only mode, sheets outside the allow-list) — all with red "Blocked" badges. Then an "Audit log" section showing a sample JSON log line in a code block, and a callout "Write tools are invisible to the AI when READ_ONLY=true."

SCREEN 4 — TOOLS REFERENCE
Docs layout. Intro line "Generated from the server's tool schemas." A filterable list of 8 tool cards: postgres_list_tables, postgres_describe_table, postgres_query, sheets_list_tabs, sheets_read_range, sheets_find_rows, sheets_append_rows, sheets_update_range. Each card: tool name in monospace, badge "read" (emerald) or "write" (amber), required scope badge (db:read / sheets:read / sheets:write), one-line description, an expandable "Input schema" table (field, type, required, description), and an "Example" code block. Write tools show a small note "Hidden when READ_ONLY=true · requires idempotency_key".

SCREEN 5 — CONFIGURATION
Docs layout. A searchable table of environment variables: Name, Default, Description, Example (DATABASE_URL, ALLOWED_SCHEMAS, ALLOWED_TABLES, QUERY_TIMEOUT_MS, MAX_ROWS, GOOGLE_SERVICE_ACCOUNT_JSON, ALLOWED_SHEET_IDS, READ_ONLY, TRANSPORT, HTTP_PORT, OAUTH_ISSUER, OAUTH_AUDIENCE, AUDIT_LOG_PATH, REDACT_ARGS, RATE_LIMIT_PER_MIN). Above it, two cards: "Local (stdio)" and "Remote (HTTP + OAuth)" with a short comparison. An alert: "Never put secrets in the client config file — use environment variables."

SCREEN 6 — CHANGELOG
Docs layout. Release timeline entries: v1.0.0 (Added / Changed / Security sections with bullet items), v0.9.0, v0.8.0. Each version with date, a "Breaking changes" amber badge where relevant, and links to the GitHub release and PyPI.
```
