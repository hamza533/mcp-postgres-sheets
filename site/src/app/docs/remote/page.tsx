import { TriangleAlertIcon } from "lucide-react";
import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export const metadata: Metadata = { title: "Remote mode & OAuth" };

const toc = [
  { id: "how-it-works", title: "How it works" },
  { id: "scopes", title: "Scopes" },
  { id: "run-it", title: "Run it" },
  { id: "try-it-locally-with-keycloak", title: "Try it locally (Keycloak)" },
  { id: "microsoft-entra-id", title: "Microsoft Entra ID" },
  { id: "endpoints", title: "Endpoints" },
];

const DOCKER_RUN = `docker run -d -p 8765:8765 \\
  -e TRANSPORT=http \\
  -e PUBLIC_URL=https://mcp.example.com \\
  -e OAUTH_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0 \\
  -e OAUTH_AUDIENCE=api://mcp-postgres-sheets \\
  -e DATABASE_URL=postgresql://mcp_readonly:…@db.internal:5432/prod \\
  -e ALLOWED_SHEET_IDS=1AbC… -e GOOGLE_SERVICE_ACCOUNT_JSON=/secrets/sa.json \\
  -v /path/to/sa.json:/secrets/sa.json:ro \\
  ghcr.io/hamza533/mcp-postgres-sheets:latest`;

const KEYCLOAK = `docker compose --profile remote up -d --wait   # Postgres + Keycloak (test only) + server on :8765
make remote-smoke                                # 13 end-to-end checks → ALL PASSED

TOKEN=$(curl -s -d grant_type=client_credentials -d client_id=mcp-reader \\
  -d client_secret=reader-dev-secret \\
  http://localhost:8180/realms/mcp/protocol/openid-connect/token | jq -r .access_token)

curl -s http://localhost:8765/mcp -H "Authorization: Bearer $TOKEN" \\
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"postgres_query","arguments":{"sql":"SELECT count(*) FROM orders"}}}'`;

const NO_TOKEN = `$ curl -i -X POST http://localhost:8765/mcp
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer error="invalid_token", error_description="Authentication required",
  resource_metadata="http://localhost:8765/.well-known/oauth-protected-resource/mcp"`;

export default function Remote() {
  return (
    <DocsShell
      title="Remote mode & OAuth"
      description="One shared server for a team, behind the identity provider you already use."
      toc={toc}
    >
      <h2 id="how-it-works">How it works</h2>
      <p>
        With <code>TRANSPORT=http</code> the server speaks MCP Streamable HTTP on <code>/mcp</code> and acts
        as an OAuth 2.1 <em>resource server</em>, as the MCP authorization spec requires. It never issues
        tokens: it validates JWT access tokens from your issuer against its JWKS (signature, <code>iss</code>,{" "}
        <code>aud</code>, <code>exp</code>), then checks the scope each tool needs.
      </p>
      <ol>
        <li>
          The client calls <code>/mcp</code> without a token and gets <code>401</code> with a pointer to the
          metadata.
        </li>
        <li>
          <code>/.well-known/oauth-protected-resource/mcp</code> names your identity provider and the
          supported scopes.
        </li>
        <li>
          The client signs the user in with that provider and retries with{" "}
          <code>Authorization: Bearer …</code>.
        </li>
      </ol>
      <CodeBlock lang="bash" title="no token" code={NO_TOKEN} />
      <p>
        The server is stateless (JSON responses, no sessions), so it scales out behind any load balancer. Each
        caller (token subject) gets <code>RATE_LIMIT_PER_MIN</code> tool calls per minute.
      </p>

      <h2 id="scopes">Scopes</h2>
      <div className="not-prose overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Scope</TableHead>
              <TableHead>Tools</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="font-mono text-xs">db:read</TableCell>
              <TableCell className="font-mono text-xs">
                postgres_list_tables, postgres_describe_table, postgres_query
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-mono text-xs">sheets:read</TableCell>
              <TableCell className="font-mono text-xs">
                sheets_list_tabs, sheets_read_range, sheets_find_rows
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-mono text-xs">sheets:write</TableCell>
              <TableCell className="font-mono text-xs">
                sheets_append_rows, sheets_update_range (only if READ_ONLY=false)
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <p>
        Scopes are read from the <code>scope</code>, <code>scp</code> and <code>roles</code> claims. Entra ID
        doesn&apos;t allow <code>:</code> in scope names, so <code>db.read</code> is accepted for{" "}
        <code>db:read</code> (and likewise for the others).
      </p>

      <h2 id="run-it">Run it</h2>
      <CodeBlock lang="bash" title="docker" code={DOCKER_RUN} />
      <p>
        Put TLS in front (Azure Container Apps, a load balancer or a reverse proxy) and set{" "}
        <code>PUBLIC_URL</code> to the public HTTPS address: it is the OAuth resource identifier.
      </p>

      <h2 id="try-it-locally-with-keycloak">Try it locally (Keycloak)</h2>
      <Alert className="border-warn/40 bg-warn-soft">
        <TriangleAlertIcon className="text-warn!" />
        <AlertTitle>The Keycloak profile is for local testing only.</AlertTitle>
        <AlertDescription>
          It runs Keycloak in dev mode with committed test secrets. Use your own identity provider in
          production.
        </AlertDescription>
      </Alert>
      <CodeBlock lang="bash" title="terminal" code={KEYCLOAK} />
      <p>
        Test clients: <code>mcp-reader</code> (db:read, sheets:read), <code>mcp-writer</code> (+
        sheets:write), <code>mcp-db-only</code> (db:read), and <code>mcp-inspector</code> (interactive login
        as <code>demo</code>/<code>demo</code>, PKCE).
      </p>

      <h2 id="microsoft-entra-id">Microsoft Entra ID</h2>
      <ol>
        <li>
          App registrations → New registration <code>mcp-postgres-sheets</code>. Under <em>Expose an API</em>{" "}
          set the Application ID URI (e.g. <code>api://mcp-postgres-sheets</code>) and add the scopes{" "}
          <code>db.read</code>, <code>sheets.read</code> and <code>sheets.write</code>.
        </li>
        <li>
          In the <em>Manifest</em>, set <code>requestedAccessTokenVersion</code> to <code>2</code> so the
          issuer is <code>https://login.microsoftonline.com/&lt;tenant-id&gt;/v2.0</code>.
        </li>
        <li>
          Register each client (or allow your users&apos; client) and grant it only the scopes it needs. For
          app-only access, create app roles with the same names instead — they arrive in the{" "}
          <code>roles</code> claim.
        </li>
        <li>
          Set <code>OAUTH_ISSUER=https://login.microsoftonline.com/&lt;tenant-id&gt;/v2.0</code> and{" "}
          <code>OAUTH_AUDIENCE</code> to the application&apos;s client ID (the <code>aud</code> of v2 tokens).
        </li>
      </ol>

      <h2 id="endpoints">Endpoints</h2>
      <ul>
        <li>
          <code>POST /mcp</code> — MCP (bearer token required)
        </li>
        <li>
          <code>GET /.well-known/oauth-protected-resource/mcp</code> — RFC 9728 metadata
        </li>
        <li>
          <code>GET /health</code> — liveness; <code>GET /ready</code> — database and Sheets credentials
          reachable (503 if not)
        </li>
      </ul>
    </DocsShell>
  );
}
