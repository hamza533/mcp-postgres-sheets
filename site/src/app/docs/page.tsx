import type { Metadata } from "next";
import Link from "next/link";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { tools } from "@/lib/data";

export const metadata: Metadata = { title: "Getting started" };

const toc = [
  { id: "what-it-is", title: "What it is" },
  { id: "how-it-works", title: "How it works" },
  { id: "try-it-in-5-minutes", title: "Try it in 5 minutes" },
  { id: "next-steps", title: "Next steps" },
];

export default function GettingStarted() {
  return (
    <DocsShell
      title="Getting started"
      description="Give an AI assistant read access to your Postgres database and Google Sheets — without giving it the keys."
      toc={toc}
    >
      <h2 id="what-it-is">What it is</h2>
      <p>
        <code>mcp-postgres-sheets</code> is a{" "}
        <a href="https://modelcontextprotocol.io">Model Context Protocol</a> server. AI clients such as Claude
        Desktop, Claude Code, Cursor and ChatGPT connect to it and get {tools.length} tools: three for
        PostgreSQL, three for reading Google Sheets, and two Sheets write tools that only exist when you turn
        off read-only mode.
      </p>
      <p>
        It is built for teams who want to ask &ldquo;what were last month&apos;s top customers?&rdquo; about
        their own data, but won&apos;t hand an AI unrestricted database or spreadsheet access.
      </p>

      <h2 id="how-it-works">How it works</h2>
      <ol>
        <li>
          The AI lists tables and describes them, then writes one SQL <code>SELECT</code>.
        </li>
        <li>
          The server parses it, checks it against the allow-lists, and runs it as a read-only role inside a
          READ ONLY transaction with a timeout and a row cap.
        </li>
        <li>Rows come back as JSON; one audit line records who asked what, and how it went.</li>
      </ol>
      <p>
        Locally it speaks <strong>stdio</strong> (no network port). Remotely it speaks{" "}
        <strong>Streamable HTTP</strong> and accepts only OAuth bearer tokens from your identity provider. See
        the <Link href="/docs/security/">security model</Link>.
      </p>

      <h2 id="try-it-in-5-minutes">Try it in 5 minutes</h2>
      <p>
        With Docker and <a href="https://docs.astral.sh/uv/">uv</a> installed, start the synthetic sample shop
        database and talk to the server with the MCP Inspector:
      </p>
      <CodeBlock
        lang="bash"
        code={`git clone https://github.com/hamza533/mcp-postgres-sheets && cd mcp-postgres-sheets
docker compose up -d db --wait          # Postgres with 500 customers, 1,500 orders + a read-only role
cp .env.example .env                    # defaults point at the sample database
SHEETS_BACKEND=memory ALLOWED_SHEET_IDS=demo-sales-pipeline \\
  npx -y @modelcontextprotocol/inspector@2.14.0 uv run mcp-postgres-sheets`}
      />
      <p>
        <code>SHEETS_BACKEND=memory</code> serves a built-in demo spreadsheet, so you can try the Sheets tools
        before creating a Google service account.
      </p>

      <h2 id="next-steps">Next steps</h2>
      <div className="not-prose grid gap-4 sm:grid-cols-2">
        {[
          ["/docs/quick-start/", "Quick start", "Connect Claude Desktop, Claude Code, Cursor or ChatGPT."],
          ["/docs/configuration/", "Configuration", "Every environment variable, with defaults."],
          ["/docs/tools/", "Tools reference", "Inputs, scopes and examples for all tools."],
          ["/docs/remote/", "Remote mode & OAuth", "Run it as a shared HTTP server behind your IdP."],
        ].map(([href, title, body]) => (
          <Link key={href} href={href!} data-slot="card-link">
            <Card className="hover:border-brand h-full transition-colors">
              <CardHeader>
                <CardTitle className="text-base">{title}</CardTitle>
                <CardDescription>{body}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </DocsShell>
  );
}
