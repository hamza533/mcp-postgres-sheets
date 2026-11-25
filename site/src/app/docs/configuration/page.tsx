import {
  ArrowRightIcon,
  CircleCheckIcon,
  ShieldCheckIcon,
  ShieldIcon,
  SlidersHorizontalIcon,
  TableIcon,
  TerminalIcon,
  type LucideIcon,
} from "lucide-react";
import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { EnvTable } from "@/components/env-table";
import { envVars } from "@/lib/data";

export const metadata: Metadata = { title: "Configuration" };

const toc = [
  { id: "execution-profiles", title: "Execution profiles" },
  { id: "security-requirement", title: "Security requirement" },
  { id: "environment-variables", title: "Environment variables" },
  { id: "production-env-example", title: "Production .env example" },
  { id: "where-settings-come-from", title: "Where settings come from" },
];

const setting = (name: string) => envVars.find((v) => v.name === name)?.default ?? "";

type Profile = {
  badge: string;
  badgeClass: string;
  corner: string;
  title: string;
  body: string;
  env: string;
  points: string[];
  pointIcon: LucideIcon;
  pointClass: string;
  footLabel: string;
  footValue: string;
};

const profiles: Profile[] = [
  {
    badge: "Desktop native",
    badgeClass: "bg-brand-soft text-brand border-brand/30",
    corner: "0 open ports",
    title: "Local mode (stdio)",
    body: "Your AI client (Claude Desktop, Claude Code, Cursor) starts the server as a subprocess on your machine.",
    env: "TRANSPORT=stdio",
    points: [
      "Talks over standard input/output — no network listener",
      "Settings from --env-file or the parent process environment",
      "Caller is recorded as local in the audit log",
    ],
    pointIcon: CircleCheckIcon,
    pointClass: "text-brand",
    footLabel: "Network exposure",
    footValue: "none",
  },
  {
    badge: "Shared server",
    badgeClass: "bg-info-soft text-info border-info/30",
    corner: "JWT bearer OAuth",
    title: "Remote mode (HTTP + OAuth)",
    body: "One server for a team behind your identity provider; needed for ChatGPT and other remote clients.",
    env: "TRANSPORT=http",
    points: [
      "Streamable HTTP, stateless — any replica answers any request",
      "Validates bearer tokens against your IdP's keys; scopes per tool",
      "Per-caller rate limit, /health and /ready endpoints",
    ],
    pointIcon: ShieldCheckIcon,
    pointClass: "text-amber-500",
    footLabel: "Default listener",
    footValue: `${setting("HTTP_HOST")}:${setting("HTTP_PORT")}`,
  },
];

const PROD_ENV = `# Production baseline (inject secrets from your secret store, not a file in the repo)
DATABASE_URL=postgresql://mcp_readonly:<from-secret-store>@db.internal:5432/analytics?sslmode=verify-full
ALLOWED_SCHEMAS=public,reporting
ALLOWED_TABLES=public.orders,public.customers,reporting.monthly_kpis
READ_ONLY=true
MAX_ROWS=500
QUERY_TIMEOUT_MS=5000
TRANSPORT=http
HTTP_HOST=0.0.0.0
HTTP_PORT=8765
PUBLIC_URL=https://mcp.example.com
OAUTH_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
OAUTH_AUDIENCE=api://mcp-postgres-sheets
RATE_LIMIT_PER_MIN=120
REDACT_ARGS=true`;

function IconHeading({ id, icon: Icon, children }: { id: string; icon: LucideIcon; children: string }) {
  return (
    <h2 id={id} className="flex items-center gap-2">
      <Icon className="text-brand size-5" /> {children}
    </h2>
  );
}

export default function Configuration() {
  return (
    <DocsShell
      title="Server Configuration"
      titleBadge="System env"
      description="All server behaviour is configured with environment variables: connection strings, safety boundaries and the transport. Defaults are the safe choice."
      toc={toc}
    >
      <div className="flex items-baseline justify-between gap-3">
        <IconHeading id="execution-profiles" icon={SlidersHorizontalIcon}>
          Execution profiles
        </IconHeading>
        <span className="label-mono text-muted-foreground hidden sm:inline">TRANSPORT selection</span>
      </div>
      <div className="not-prose mt-4 grid gap-4 sm:grid-cols-2">
        {profiles.map((p) => (
          <div key={p.title} className="bg-card flex flex-col rounded-lg border p-5">
            <div className="flex items-center justify-between gap-2">
              <span className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${p.badgeClass}`}>
                {p.badge}
              </span>
              <span className="text-muted-foreground font-mono text-[11px]">{p.corner}</span>
            </div>
            <p className="mt-3 font-semibold">{p.title}</p>
            <p className="text-foreground/75 mt-1 text-sm leading-6">{p.body}</p>
            <div className="bg-sidebar mt-4 flex items-center gap-2 rounded-sm border px-3 py-2 font-mono text-xs">
              <TerminalIcon className="text-muted-foreground size-3.5" />
              {p.env}
              <ArrowRightIcon className="text-muted-foreground ml-auto size-3.5" />
            </div>
            <ul className="mt-4 space-y-2 text-[13px] leading-5">
              {p.points.map((point) => (
                <li key={point} className="flex gap-2">
                  <p.pointIcon className={`mt-0.5 size-3.5 shrink-0 ${p.pointClass}`} />
                  <span className="text-foreground/80">{point}</span>
                </li>
              ))}
            </ul>
            <div className="mt-auto flex items-center justify-between border-t pt-3 text-xs">
              <span className="label-mono text-muted-foreground normal-case">{p.footLabel}</span>
              <span className="text-brand font-mono font-semibold">{p.footValue}</span>
            </div>
          </div>
        ))}
      </div>

      <div
        id="security-requirement"
        className="not-prose border-warn/25 bg-warn-soft mt-8 flex scroll-mt-20 gap-4 rounded-lg border p-5"
        role="note"
      >
        <span className="grid size-9 shrink-0 place-items-center rounded-md bg-amber-600 text-white">
          <ShieldIcon className="size-4" />
        </span>
        <div className="text-sm">
          <p className="flex items-center gap-2 font-semibold">
            Security requirement
            <span className="rounded-sm border border-amber-300 bg-amber-100 px-1.5 font-mono text-[10px] text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              STRICT
            </span>
          </p>
          <p className="text-foreground/80 mt-1 leading-6">
            Never put database passwords, connection strings or the service-account key in a client config
            file such as{" "}
            <code className="bg-background rounded-sm border px-1 font-mono text-xs">
              claude_desktop_config.json
            </code>
            . Pass <code className="bg-background rounded-sm border px-1 font-mono text-xs">--env-file</code>{" "}
            pointing at a file only you can read, or inject variables from a secret store (Azure Key Vault,
            1Password CLI, AWS Secrets Manager) in production.
          </p>
        </div>
      </div>

      <IconHeading id="environment-variables" icon={TableIcon}>
        Environment variables
      </IconHeading>
      <p>Read once at start-up. Lists are comma-separated; booleans are true or false.</p>
      <EnvTable variables={envVars} />

      <IconHeading id="production-env-example" icon={TerminalIcon}>
        Production .env example
      </IconHeading>
      <CodeBlock lang="ini" title=".env.production" code={PROD_ENV} />

      <h2 id="where-settings-come-from">Where settings come from</h2>
      <p>In order of precedence (highest first):</p>
      <ol>
        <li>Real environment variables of the server process.</li>
        <li>
          The file given with <code>--env-file</code>, otherwise <code>.env</code> in the working directory.
        </li>
        <li>The defaults above.</li>
      </ol>
      <p>Invalid values stop the server at start-up with a clear message — never mid-session:</p>
      <CodeBlock
        lang="text"
        title="stderr"
        code={`mcp-postgres-sheets: invalid configuration — config: Value error, TRANSPORT=http requires OAuth: set OAUTH_ISSUER and OAUTH_AUDIENCE.`}
      />
    </DocsShell>
  );
}
