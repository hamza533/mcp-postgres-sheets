import { KeyRoundIcon, LaptopIcon } from "lucide-react";
import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { EnvTable } from "@/components/env-table";
import { Callout } from "@/components/callout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { envVars } from "@/lib/data";

export const metadata: Metadata = { title: "Configuration" };

const toc = [
  { id: "local-or-remote", title: "Local or remote" },
  { id: "environment-variables", title: "Environment variables" },
  { id: "where-settings-come-from", title: "Where settings come from" },
];

export default function Configuration() {
  return (
    <DocsShell
      title="Configuration"
      description="Everything is configured with environment variables. Defaults are the safe choice."
      toc={toc}
    >
      <h2 id="local-or-remote">Local or remote</h2>
      <div className="not-prose grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <LaptopIcon className="text-brand size-5" /> Local (stdio)
            </CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground space-y-2 text-sm">
            <p>Your AI client starts the server as a subprocess. No network port, no tokens.</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>
                Caller is <code>local</code> in the audit log
              </li>
              <li>Best for one person on one machine</li>
              <li>
                <code>TRANSPORT=stdio</code> (default)
              </li>
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRoundIcon className="text-brand size-5" /> Remote (HTTP + OAuth)
            </CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground space-y-2 text-sm">
            <p>One shared server behind your identity provider; every request carries a bearer token.</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>Scopes per tool, rate limit per caller</li>
              <li>Needed for ChatGPT and for teams</li>
              <li>
                <code>TRANSPORT=http</code> + <code>OAUTH_ISSUER</code> + <code>OAUTH_AUDIENCE</code>
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
      <Callout
        variant="security"
        className="mt-6"
        title="Never put secrets in the client config file — use environment variables."
      >
        Pass <code>--env-file</code> pointing at a file only you can read (or inject variables from a secret
        store in production). Client config files are often synced, shared or pasted into issues.
      </Callout>

      <h2 id="environment-variables">Environment variables</h2>
      <EnvTable variables={envVars} />

      <h2 id="where-settings-come-from">Where settings come from</h2>
      <p>In order of precedence (highest first):</p>
      <ol>
        <li>Real environment variables of the server process.</li>
        <li>
          The file given with <code>--env-file</code>, otherwise <code>.env</code> in the working directory.
        </li>
        <li>The defaults above.</li>
      </ol>
      <p>
        Lists are comma-separated. Invalid values stop the server at start-up with a clear message — never
        mid-session:
      </p>
      <CodeBlock
        lang="text"
        title="stderr"
        code={`mcp-postgres-sheets: invalid configuration — config: Value error, TRANSPORT=http requires OAuth: set OAUTH_ISSUER and OAUTH_AUDIENCE.`}
      />
    </DocsShell>
  );
}
