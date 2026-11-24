import { CircleCheckIcon, ShieldCheckIcon, WorkflowIcon } from "lucide-react";
import type { Metadata } from "next";

import { Callout, SuccessBanner } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { Pill } from "@/components/pill";
import { PromptList } from "@/components/prompt-list";
import { StepHeading } from "@/components/step-heading";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const metadata: Metadata = { title: "Quick start" };

const toc = [
  { id: "1-create-a-read-only-database-role", title: "1. Create a read-only role" },
  { id: "2-share-your-google-sheet", title: "2. Share your Google Sheet" },
  { id: "3-add-the-server-to-your-ai-client", title: "3. Add server to AI client" },
  { id: "4-try-it", title: "4. Try it out" },
];

const facts = [
  { label: "Transport", value: "stdio · Streamable HTTP" },
  {
    label: "Default mode",
    value: (
      <span className="text-brand inline-flex items-center gap-1.5">
        <ShieldCheckIcon className="size-3.5" /> Read-only enforced
      </span>
    ),
  },
  { label: "Tools", value: "8 tools · 6 in read-only mode" },
];

const PROMPTS = [
  "What tables are in the database, and what does the orders table look like?",
  "Who were our top 5 customers by revenue last quarter?",
  "How many leads are in the Won stage in the sales pipeline sheet?",
  "Delete all cancelled orders.",
];

const tocNote = (
  <div className="bg-sidebar rounded-lg border p-3 text-xs leading-5">
    <p className="label-mono text-brand mb-1 flex items-center gap-1.5 normal-case">
      <CircleCheckIcon className="size-3.5" /> Zero-write guarantee
    </p>
    <p className="text-muted-foreground">
      DDL and DML are rejected by the SQL check, run inside a READ ONLY transaction, and the database role
      can&apos;t write anyway.
    </p>
  </div>
);

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
      eyebrow="5-minute setup"
      description="Four steps from zero to asking your AI assistant about your own data, with read-only access and an audit log from the first call."
      facts={facts}
      toc={toc}
      tocNote={tocNote}
    >
      <StepHeading n={1} id="1-create-a-read-only-database-role">
        Create a read-only database role
      </StepHeading>
      <p>
        This role is the main safety guarantee: even if every other layer failed, it can only read what you
        grant here. The full, idempotent script is <code>deploy/sql/001_readonly_role.sql</code>.
      </p>
      <CodeBlock lang="sql" title="001_readonly_role.sql" code={ROLE_SQL} />

      <StepHeading n={2} id="2-share-your-google-sheet">
        Share your Google Sheet with the service account
      </StepHeading>
      <p>
        In Google Cloud, create a service account, enable the Google Sheets API and download a JSON key. Then
        open your spreadsheet, click <strong>Share</strong> and add the service account&apos;s email (it looks
        like <code>name@project.iam.gserviceaccount.com</code>). Add the sheet&apos;s ID — the long part of
        its URL — to <code>ALLOWED_SHEET_IDS</code>.
      </p>
      <Callout variant="info" title="Least privilege: only the sheets you share — and allow-list">
        The service account sees nothing until you share a sheet with it, and the server refuses any
        spreadsheet ID that is not in <code>ALLOWED_SHEET_IDS</code>. Give it <strong>Viewer</strong> access
        unless you plan to enable the write tools.
      </Callout>
      <p>Put the settings in an env file that only you can read:</p>
      <CodeBlock lang="ini" title=".env" code={ENV_FILE} />

      <StepHeading n={3} id="3-add-the-server-to-your-ai-client">
        Add the server to your AI client
      </StepHeading>
      <p>
        Local clients start the server over stdio; ChatGPT connects to a remote server over Streamable HTTP
        with OAuth. Pick your client:
      </p>
      <Tabs defaultValue="claude-desktop" className="my-4">
        <TabsList className="bg-sidebar h-auto w-full flex-wrap justify-start rounded-lg border p-1">
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

      <StepHeading n={4} id="4-try-it">
        Try it
      </StepHeading>
      <p>
        Restart your client and ask in plain language. The assistant discovers the tables and tabs itself; the
        last prompt is there to watch a write get refused.
      </p>
      <PromptList prompts={PROMPTS} />

      <figure className="my-6 rounded-lg border" aria-label="Example tool call">
        <figcaption className="label-mono text-muted-foreground flex items-center justify-between border-b px-4 py-2.5">
          <span className="flex items-center gap-2">
            <WorkflowIcon className="size-3.5" /> Example tool call
          </span>
          <span className="text-brand normal-case">one audit line per call</span>
        </figcaption>
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 font-mono text-[13px]">
          <span className="font-semibold">postgres_query</span>
          <Pill tone="read">READ</Pill>
          <span className="text-muted-foreground ml-auto">outcome: ok · rows: 5 · max_rows: 500</span>
        </div>
      </figure>

      <SuccessBanner title="You're connected — ask a question about your data." data-testid="success-alert">
        Your client now lists the tools this server exposes. Every call is written to your audit log.
      </SuccessBanner>
    </DocsShell>
  );
}
