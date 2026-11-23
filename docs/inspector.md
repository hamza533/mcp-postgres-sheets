# Testing with the MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the official tool for
poking at an MCP server by hand. Both transports were verified with Inspector **2.14.0**.

## Local (stdio)

```bash
make db                                   # sample Postgres on localhost:5544
cp .env.example .env                      # defaults point at the sample database
make inspector                            # = npx -y @modelcontextprotocol/inspector@2.14.0 uv run mcp-postgres-sheets
```

The web UI opens on http://localhost:6274. Click **Connect**, then **Tools → List tools**. Try
`postgres_query` with `SELECT segment, count(*) FROM customers GROUP BY 1`, then
`DROP TABLE customers` — the second one comes back as `Rejected: only a single SELECT is allowed`.

Headless (CLI mode) — Inspector options go **before** `--`, the server command after it:

```bash
npx -y @modelcontextprotocol/inspector@2.14.0 --cli --method tools/list -- uv run mcp-postgres-sheets

npx -y @modelcontextprotocol/inspector@2.14.0 --cli \
  --method tools/call --tool-name postgres_query \
  --tool-arg "sql=SELECT count(*) FROM orders" \
  -- uv run mcp-postgres-sheets
```

Using the Docker image instead of uv:

```bash
npx -y @modelcontextprotocol/inspector@2.14.0 --cli --method tools/list -- \
  docker run --rm -i --network mcp-postgres-sheets_default \
  -e DATABASE_URL=postgresql://mcp_readonly:mcp_readonly@db:5432/shop \
  -e SHEETS_BACKEND=memory -e ALLOWED_SHEET_IDS=demo-sales-pipeline \
  mcp-postgres-sheets:dev
```

## Remote (Streamable HTTP + OAuth)

```bash
docker compose --profile remote up -d --wait     # Postgres + Keycloak (test only) + server on :8765
make remote-smoke                                 # 13 end-to-end checks, prints PASS/FAIL
```

Get a token from the test Keycloak (client-credentials grant) and call a tool:

```bash
TOKEN=$(curl -s -d grant_type=client_credentials -d client_id=mcp-reader -d client_secret=reader-dev-secret \
  http://localhost:8180/realms/mcp/protocol/openid-connect/token | jq -r .access_token)

npx -y @modelcontextprotocol/inspector@2.14.0 --cli http://localhost:8765/mcp \
  --header "Authorization: Bearer $TOKEN" \
  --method tools/call --tool-name postgres_query --tool-arg "sql=SELECT count(*) FROM customers"
```

Test clients in the realm (`deploy/keycloak/mcp-realm.json`, **local testing only**):

| Client | Secret | Scopes |
|---|---|---|
| `mcp-reader` | `reader-dev-secret` | `db:read sheets:read` |
| `mcp-writer` | `writer-dev-secret` | `db:read sheets:read sheets:write` |
| `mcp-db-only` | `db-only-dev-secret` | `db:read` |
| `mcp-inspector` | public, PKCE | interactive login as `demo` / `demo` from the Inspector UI |

In the Inspector **web UI**, choose transport *Streamable HTTP*, URL `http://localhost:8765/mcp`,
then *Open Auth Settings → Quick OAuth Flow* with client ID `mcp-inspector`: the server's 401
points the Inspector at the protected-resource metadata, which names Keycloak as the
authorization server.
