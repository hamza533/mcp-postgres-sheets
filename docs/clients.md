# Client setup guides

Every local setup starts the server with `uvx` (no install step) and reads its settings from an
env file you control, so secrets never sit in a client's config file:

```ini
# ~/.config/mcp-postgres-sheets/.env   (chmod 600)
DATABASE_URL=postgresql://mcp_readonly:<password>@localhost:5432/mydb
ALLOWED_SCHEMAS=public
GOOGLE_SERVICE_ACCOUNT_JSON=/Users/me/.config/mcp-postgres-sheets/service-account.json
ALLOWED_SHEET_IDS=1AbC…your-sheet-id
READ_ONLY=true
AUDIT_LOG_PATH=/Users/me/.config/mcp-postgres-sheets/audit.jsonl
```

Trying it with the repo's sample database instead? Use the repo's `.env` (from `.env.example`) and add
`SHEETS_BACKEND=memory` and `ALLOWED_SHEET_IDS=demo-sales-pipeline` for the built-in demo spreadsheet.

> **`uvx` not found from a desktop app?** GUI apps often don't see your shell's `PATH`. Use the absolute
> path from `which uvx` (macOS/Linux, e.g. `/Users/me/.local/bin/uvx`) or `where uvx` (Windows).
>
> **Prefer Docker?** Replace the command with
> `docker run --rm -i --env-file /path/to/.env ghcr.io/hamza533/mcp-postgres-sheets:0.1.0`
> (use `host.docker.internal` instead of `localhost` in `DATABASE_URL`).

## Claude Desktop

Settings → Developer → **Edit Config** opens `claude_desktop_config.json`
(macOS `~/Library/Application Support/Claude/`, Windows `%APPDATA%\Claude\`). Add:

```json
{
  "mcpServers": {
    "postgres-sheets": {
      "command": "uvx",
      "args": ["mcp-postgres-sheets", "--env-file", "/Users/me/.config/mcp-postgres-sheets/.env"]
    }
  }
}
```

Windows paths in JSON need escaped backslashes: `"C:\\Users\\me\\.config\\mcp-postgres-sheets\\.env"`.
Restart Claude Desktop; the tools appear under the tools icon in the chat box.

**Remote server** (team setup): Settings → Connectors → **Add custom connector** with URL
`https://mcp.example.com/mcp`; Claude walks you through your identity provider's sign-in.

## Claude Code

```bash
claude mcp add postgres-sheets -- uvx mcp-postgres-sheets --env-file ~/.config/mcp-postgres-sheets/.env
```

Add `--scope project` to write it to the repo's `.mcp.json` for your team (each person keeps their own
env file). Check it with `claude mcp list`.

**Remote server:**

```bash
claude mcp add --transport http postgres-sheets https://mcp.example.com/mcp
```

Then run `/mcp` inside Claude Code to sign in with your identity provider.

## Cursor

Add to `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one project):

```json
{
  "mcpServers": {
    "postgres-sheets": {
      "command": "uvx",
      "args": ["mcp-postgres-sheets", "--env-file", "/Users/me/.config/mcp-postgres-sheets/.env"]
    }
  }
}
```

Open Cursor Settings → MCP to check the server is green and its 6 tools (8 with `READ_ONLY=false`) are
listed. **Remote server:** `{ "mcpServers": { "postgres-sheets": { "url": "https://mcp.example.com/mcp" } } }`.

## ChatGPT (remote connector)

ChatGPT only connects to **remote** MCP servers, so run the server in remote mode first (Azure profile,
`render.yaml`, or `docker run … -e TRANSPORT=http`, see the README) behind an OIDC provider that supports
the clients ChatGPT registers.

1. In ChatGPT, open Settings → **Apps & Connectors** → Advanced settings and turn on **Developer mode**
   (available on plans that support custom connectors; menu names change, see OpenAI's help pages).
2. **Create** a connector: name `PG Sheets`, MCP server URL `https://mcp.example.com/mcp`,
   authentication **OAuth**.
3. ChatGPT calls the server, receives `401` with the protected-resource metadata, discovers your identity
   provider, and signs you in. Grant only the scopes you need (`db:read`, `sheets:read`).
4. In a chat, enable the connector from the tools menu and ask a question about your data.

## Check what the AI sees

Whatever the client, the MCP Inspector shows exactly the tools and schemas the AI receives:
see [inspector.md](inspector.md).
