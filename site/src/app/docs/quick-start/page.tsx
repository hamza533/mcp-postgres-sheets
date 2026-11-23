import { CircleCheckIcon, InfoIcon } from "lucide-react";
import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const metadata: Metadata = { title: "Quick start" };

const toc = [
  { id: "1-create-a-read-only-database-role", title: "1. Create a read-only role" },
  { id: "2-share-your-google-sheet", title: "2. Share your Google Sheet" },
  { id: "3-add-the-server-to-your-ai-client", title: "3. Add it to your AI client" },
  { id: "4-try-it", title: "4. Try it" },
];

const ROLE_SQL = `-- Run as the database owner. Grants SELECT on one schema and nothing else.
CREATE ROLE mcp_readonly LOGIN PASSWORD 'choose-a-long-random-password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
ALTER ROLE mcp_readonly SET default_transaction_read_only = on;
ALTER ROLE mcp_readonly SET statement_timeout = '5s';
GRANT CONNECT ON DATABASE mydb TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_readonly;`;

const ENV_FILE = `# ~/.config/mcp-postgres-sheets/.env   (chmod 600 — secrets live here, not in the client config)
DATABASE_URL=postgresql://mcp_readonly:<password>@localhost:5432/mydb
ALLOWED_SCHEMAS=public
GOOGLE_SERVICE_ACCOUNT_JSON=/Users/me/.config/mcp-postgres-sheets/service-account.json
ALLOWED_SHEET_IDS=1AbC…your-sheet-id
READ_ONLY=true
AUDIT_LOG_PATH=/Users/me/.config/mcp-postgres-sheets/audit.jsonl`;

const CLAUDE_DESKTOP = `{
  "mcpServers": {
    "postgres-sheets": {
      "command": "uvx",
      "args": [
        "mcp-postgres-sheets",
        "--env-file",
        "/Users/me/.config/mcp-postgres-sheets/.env"
      ]
    }
  }
}`;

const CLAUDE_CODE = `claude mcp add postgres-sheets -- \\
  uvx mcp-postgres-sheets --env-file ~/.config/mcp-postgres-sheets/.env`;

const CURSOR = `{
  "mcpServers": {
    "postgres-sheets": {
      "command": "uvx",
      "args": ["mcp-postgres-sheets", "--env-file", "/Users/me/.config/mcp-postgres-sheets/.env"]
    }
  }
}`;

const CHATGPT = `Server URL:      https://mcp.example.com/mcp
Authentication:  OAuth
                 (ChatGPT discovers your identity provider from the server's
                  /.well-known/oauth-protected-resource metadata)`;

export default function QuickStart() {
  return (
    <DocsShell
      title="Quick start"
      description="Four steps from zero to asking your AI assistant about your own data."
      toc={toc}
    >
      <h2 id="1-create-a-read-only-database-role">1. Create a read-only database role</h2>
      <p>
        This role is the main safety guarantee: even if every other layer failed, it can only read what you
        grant here. The full, idempotent script is <code>deploy/sql/001_readonly_role.sql</code>.
      </p>
      <CodeBlock lang="sql" title="read-only role" code={ROLE_SQL} />

      <h2 id="2-share-your-google-sheet">2. Share your Google Sheet with the service account</h2>
      <p>
        In Google Cloud, create a service account, enable the Google Sheets API and download a JSON key. Then
        open your spreadsheet, click <strong>Share</strong> and add the service account&apos;s email (it looks
        like <code>name@project.iam.gserviceaccount.com</code>). Add the sheet&apos;s ID — the long part of
        its URL — to <code>ALLOWED_SHEET_IDS</code>.
      </p>
      <Alert>
        <InfoIcon />
        <AlertTitle>Only the sheets you share — and allow-list — are reachable</AlertTitle>
        <AlertDescription>
          The service account sees nothing until you share a sheet with it, and the server refuses any
          spreadsheet ID that is not in ALLOWED_SHEET_IDS. Give it Viewer access unless you plan to enable the
          write tools.
        </AlertDescription>
      </Alert>
      <p>Put the settings in an env file that only you can read:</p>
      <CodeBlock lang="ini" title=".env" code={ENV_FILE} />

      <h2 id="3-add-the-server-to-your-ai-client">3. Add the server to your AI client</h2>
      <Tabs defaultValue="claude-desktop" className="my-4">
        <TabsList className="flex-wrap">
          <TabsTrigger value="claude-desktop">Claude Desktop</TabsTrigger>
          <TabsTrigger value="claude-code">Claude Code</TabsTrigger>
          <TabsTrigger value="cursor">Cursor</TabsTrigger>
          <TabsTrigger value="chatgpt">ChatGPT (remote)</TabsTrigger>
        </TabsList>
        <TabsContent value="claude-desktop">
          <p>
            Settings → Developer → Edit Config opens <code>claude_desktop_config.json</code>. Add the server
            and restart Claude Desktop:
          </p>
          <CodeBlock lang="json" title="claude_desktop_config.json" code={CLAUDE_DESKTOP} />
        </TabsContent>
        <TabsContent value="claude-code">
          <p>
            One command (add <code>--scope project</code> to share it with your team via{" "}
            <code>.mcp.json</code>):
          </p>
          <CodeBlock lang="bash" title="terminal" code={CLAUDE_CODE} />
        </TabsContent>
        <TabsContent value="cursor">
          <p>
            Add to <code>~/.cursor/mcp.json</code> (all projects) or <code>.cursor/mcp.json</code> (one
            project):
          </p>
          <CodeBlock lang="json" title="mcp.json" code={CURSOR} />
        </TabsContent>
        <TabsContent value="chatgpt">
          <p>
            ChatGPT connects to remote MCP servers only. Run the server in{" "}
            <a href="/docs/remote/">remote mode</a> behind your identity provider, then in ChatGPT open
            Settings → Connectors → Create (developer mode) and enter:
          </p>
          <CodeBlock lang="text" title="custom connector" code={CHATGPT} />
        </TabsContent>
      </Tabs>

      <h2 id="4-try-it">4. Try it</h2>
      <p>Ask your assistant questions like these:</p>
      <ul>
        <li>&ldquo;What tables are in the database, and what does the orders table look like?&rdquo;</li>
        <li>&ldquo;Who were our top 5 customers by revenue last quarter?&rdquo;</li>
        <li>&ldquo;How many leads are in the Won stage in the sales pipeline sheet?&rdquo;</li>
        <li>&ldquo;Delete all cancelled orders.&rdquo; — and watch it get refused.</li>
      </ul>
      <Alert className="border-brand/40 bg-brand-soft" data-testid="success-alert">
        <CircleCheckIcon className="text-brand!" />
        <AlertTitle>You&apos;re connected — ask a question about your data.</AlertTitle>
        <AlertDescription>Every call is now written to your audit log.</AlertDescription>
      </Alert>
    </DocsShell>
  );
}
