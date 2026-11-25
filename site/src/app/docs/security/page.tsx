import {
  ArrowDownIcon,
  CircleDotIcon,
  DatabaseIcon,
  FilterIcon,
  KeyRoundIcon,
  LayersIcon,
  LockIcon,
  ScanSearchIcon,
  ShieldCheckIcon,
  ShieldIcon,
  type LucideIcon,
} from "lucide-react";
import type { Metadata } from "next";

import { Callout } from "@/components/callout";
import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { Pill } from "@/components/pill";
import { SectionHeading } from "@/components/section-heading";
import { envVars, results } from "@/lib/data";

export const metadata: Metadata = { title: "Security model" };

const toc = [
  { id: "five-layers", title: "Layered defense architecture" },
  { id: "what-is-blocked", title: "What is blocked" },
  { id: "all-safety-cases", title: "All safety cases", level: 3 as const },
  { id: "audit-log", title: "Audit log" },
  { id: "what-it-does-not-do", title: "What it does not do" },
];

const setting = (name: string) => envVars.find((v) => v.name === name)?.default ?? "";

type Layer = {
  icon: LucideIcon;
  title: string;
  note?: string;
  body: string;
  chips?: string[];
  chip?: string;
  darkChip?: string;
  code?: string;
};

const layers: Layer[] = [
  {
    icon: KeyRoundIcon,
    title: "OAuth 2.1 scopes",
    note: "remote mode only",
    body: "Bearer JWTs are checked against your identity provider's keys (signature, issuer, audience, expiry); each tool needs its own scope.",
    chips: ["db:read", "sheets:read", "sheets:write"],
  },
  {
    icon: FilterIcon,
    title: "Resource allow-lists",
    body: "Checked before anything runs: a schema, table or spreadsheet that is not listed is rejected with a message the AI can act on.",
    chips: ["ALLOWED_SCHEMAS", "ALLOWED_TABLES", "ALLOWED_SHEET_IDS"],
  },
  {
    icon: ScanSearchIcon,
    title: "SQL syntax-tree inspection",
    body: "Parsed with sqlglot: exactly one SELECT. No DDL or DML, no data-modifying CTEs, no SELECT INTO or locking clauses, no pg_* catalogs, no unsafe functions.",
    chip: "single SELECT only",
  },
  {
    icon: LayersIcon,
    title: "Read-only transaction",
    body: "Each query runs in its own transaction that is always rolled back, with a statement timeout and a row cap read through a server-side cursor.",
    darkChip: `MAX_ROWS=${setting("MAX_ROWS")}`,
    code: `BEGIN READ ONLY; SET LOCAL statement_timeout = '${setting("QUERY_TIMEOUT_MS")}ms'; SET LOCAL search_path = <allowed schemas>`,
  },
  {
    icon: DatabaseIcon,
    title: "Read-only database role",
    body: "The main guarantee: the server connects as a role that can only SELECT. Even if every layer above were bypassed, Postgres itself refuses the write.",
    chip: "SELECT only",
  },
];

type Highlight = { id: string; category: string; sub: string; result: string };

/** Real safety-suite cases with the exact message the server returns. */
const highlights: Highlight[] = [
  {
    id: "dml-drop-table",
    category: "DROP / ALTER / TRUNCATE",
    sub: "Destructive DDL",
    result: "Rejected: only a single SELECT is allowed (got DROP)",
  },
  {
    id: "multi-select-drop",
    category: "Multiple statements",
    sub: "Chained with ;",
    result: "Rejected: only a single SELECT is allowed (found 2 statements)",
  },
  {
    id: "cte-delete",
    category: "Write hidden in a CTE",
    sub: "Data-modifying WITH",
    result: "Rejected: DELETE is not allowed inside a query; only reads are permitted",
  },
  {
    id: "fn-pg-sleep",
    category: "Sleep / side channel",
    sub: "Unsafe functions",
    result: "Rejected: function pg_sleep() is not allowed",
  },
  {
    id: "limit-huge-result",
    category: "Huge result sets",
    sub: "Memory exfiltration",
    result: "Runs, but only MAX_ROWS rows come back (truncated=true)",
  },
  {
    id: "sheets-append-read-only",
    category: "Write tools in read-only mode",
    sub: "Tool not registered",
    result: "Unknown tool: sheets_append_rows (not registered when READ_ONLY=true)",
  },
  {
    id: "sheets-read-not-allowed",
    category: "Out-of-scope sheets",
    sub: "Resource traversal",
    result: "Rejected: spreadsheet demo-hr-private is not in ALLOWED_SHEET_IDS",
  },
];

const OUTCOME_PILL: Record<string, { tone: "blocked" | "write"; label: string }> = {
  capped: { tone: "write", label: "Capped" },
  not_listed: { tone: "blocked", label: "Hidden" },
};

const AUDIT_LINE = `{"ts":"2026-11-23T11:59:35.510Z","type":"audit","request_id":"9d82398322e2423fb39c527a07afa45d",
 "caller":"57fe362a-3766-4c62-b5a1-08dd3a3d7c81","client_id":"mcp-reader","transport":"http",
 "tool":"postgres_query","args":{"sql":{"redacted":true,"sha256":"a4c442a19d3f4f0c","len":20}},
 "duration_ms":0.5,"row_count":null,"outcome":"blocked",
 "error":"Rejected: only a single SELECT is allowed (got DROP)"}`;

export default function Security() {
  const { cases, passed, total, byCategory } = results.safety;
  const byId = Object.fromEntries(cases.map((c) => [c.id, c]));
  return (
    <DocsShell
      title="Security Model & Guardrails"
      eyebrow="zero-trust guardrails"
      eyebrowNote={
        <>
          <ShieldCheckIcon className="size-3.5" /> Read-only by default
        </>
      }
      description="Defence in depth, designed so that an untrusted or hallucinating model cannot change or leak your data. Five independent layers, each enough to stop a whole class of mistakes."
      factStyle="cards"
      facts={[
        {
          label: "Guard layers",
          value: "5 layers",
          detail: "From token scopes to the database role",
          icon: <ShieldIcon className="size-4" />,
        },
        {
          label: "Query analysis",
          value: "Syntax tree",
          detail: "Parsed with sqlglot, not matched with regexes",
          icon: <ScanSearchIcon className="size-4" />,
        },
        {
          label: "Safety suite",
          value: <span className="text-brand">{`${passed}/${total} stopped`}</span>,
          detail: "Attack cases run in CI on every push",
          icon: <LockIcon className="size-4" />,
        },
      ]}
      toc={toc}
    >
      <SectionHeading n={1} id="five-layers">
        Layered defense architecture
      </SectionHeading>
      <p>
        A request passes through every layer, top to bottom. If any one of them says no, the request stops
        there — and the bottom layer alone already prevents any write.
      </p>
      <ol className="not-prose my-6" aria-label="Safety layers" data-testid="layers">
        {layers.map((layer, i) => (
          <li key={layer.title}>
            <div className="bg-card flex gap-4 rounded-lg border p-4 shadow-[0_1px_2px_0_rgba(0,0,0,0.05)]">
              <span className="bg-info-soft text-info grid size-9 shrink-0 place-items-center rounded-md">
                <layer.icon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="label-mono text-brand flex items-center gap-1.5">
                      Layer {i + 1} <CircleDotIcon className="size-2.5" />
                    </p>
                    <p className="mt-0.5 font-semibold">
                      {layer.title}{" "}
                      {layer.note ? (
                        <span className="text-muted-foreground text-xs font-normal">({layer.note})</span>
                      ) : null}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {layer.chips?.map((c) => (
                      <span
                        key={c}
                        className="bg-muted rounded-sm border px-1.5 py-0.5 font-mono text-[11px]"
                      >
                        {c}
                      </span>
                    ))}
                    {layer.chip ? (
                      <span className="bg-info-soft text-foreground rounded-full border px-2 py-0.5 font-mono text-[11px] font-semibold">
                        {layer.chip}
                      </span>
                    ) : null}
                    {layer.darkChip ? (
                      <span className="bg-code rounded-sm px-2 py-0.5 font-mono text-[11px] text-emerald-300">
                        {layer.darkChip}
                      </span>
                    ) : null}
                  </div>
                </div>
                <p className="text-foreground/75 mt-1 text-sm leading-6">{layer.body}</p>
                {layer.code ? (
                  <code className="bg-muted mt-3 block overflow-x-auto rounded-sm border px-3 py-2 font-mono text-xs">
                    {layer.code}
                  </code>
                ) : null}
              </div>
            </div>
            {i < layers.length - 1 ? (
              <div className="flex justify-center py-1.5" aria-hidden="true">
                <span className="bg-info-soft text-info grid size-5 place-items-center rounded-full border">
                  <ArrowDownIcon className="size-3" />
                </span>
              </div>
            ) : null}
          </li>
        ))}
      </ol>

      <SectionHeading
        n={2}
        id="what-is-blocked"
        aside={
          <>
            <span className="bg-danger size-1.5 rounded-full" /> {passed}/{total} stopped
          </>
        }
      >
        What is blocked
      </SectionHeading>
      <p>
        The safety suite sends {total} attack and misuse attempts through a real MCP session in CI.{" "}
        <strong>
          {passed}/{total}
        </strong>{" "}
        are stopped, and the build fails on any regression. Some of them:
      </p>
      <div className="not-prose overflow-x-auto rounded-lg border">
        <table className="w-full text-left text-sm">
          <thead className="bg-sidebar border-b">
            <tr className="label-mono text-muted-foreground">
              <th className="px-4 py-2.5 font-medium">Attempt category</th>
              <th className="px-4 py-2.5 font-medium">Example payload</th>
              <th className="px-4 py-2.5 font-medium">Server result</th>
            </tr>
          </thead>
          <tbody>
            {highlights.map((h) => {
              const c = byId[h.id];
              if (!c) return null;
              const pill = OUTCOME_PILL[c.outcome] ?? { tone: "blocked" as const, label: "Blocked" };
              return (
                <tr key={h.id} className="border-b align-top last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-semibold">{h.category}</p>
                    <p className="text-muted-foreground font-mono text-[11px]">{h.sub}</p>
                  </td>
                  <td className="max-w-64 px-4 py-3">
                    <code className="bg-muted block rounded-sm border px-2 py-1 font-mono text-xs break-words">
                      {c.tool === "postgres_query" ? c.example : `${c.tool}(…)`}
                    </code>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-start gap-2">
                      <Pill tone={pill.tone}>{pill.label}</Pill>
                      <span className="text-foreground/75 text-xs leading-5">{h.result}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h3 id="all-safety-cases">All safety cases</h3>
      <details className="rounded-lg border p-4" data-testid="all-cases">
        <summary className="cursor-pointer font-medium">Show all {cases.length} cases by category</summary>
        <div className="mt-4 space-y-4">
          {Object.entries(byCategory).map(([category, score]) => (
            <div key={category}>
              <p className="text-sm font-semibold">
                {category}{" "}
                <span className="text-muted-foreground font-normal">
                  {score.passed}/{score.total}
                </span>
              </p>
              <ul className="not-prose mt-1 space-y-1 text-sm">
                {cases
                  .filter((c) => c.category === category)
                  .map((c) => (
                    <li key={c.id} className="flex items-baseline gap-2">
                      <Pill tone="blocked">{c.outcome.replace("_", " ")}</Pill>
                      <span>{c.title}</span>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </div>
      </details>

      <SectionHeading n={3} id="audit-log">
        Audit log
      </SectionHeading>
      <p>
        Every tool call — including rejected, invalid and unknown-tool calls — writes exactly one JSON line,
        ready for Log Analytics, CloudWatch or your SIEM. Argument values are replaced by a fingerprint by
        default (<code>REDACT_ARGS=true</code>); identifiers such as table and sheet IDs are kept so the log
        stays useful. In remote mode the caller is the token&apos;s subject.
      </p>
      <CodeBlock lang="json" title="audit.jsonl" code={AUDIT_LINE} />
      <Callout variant="warning" title="Write-mode protection">
        Write tools are invisible to the AI when <code>READ_ONLY=true</code>: they are not registered, so they
        never appear in <code>tools/list</code>. When writes are enabled, every write needs an{" "}
        <code>idempotency_key</code>, so a retried call never writes twice.
      </Callout>

      <SectionHeading n={4} id="what-it-does-not-do">
        What it does not do
      </SectionHeading>
      <ul>
        <li>
          <strong>No database writes, ever.</strong> There is no tool for it, by design. Use your normal
          migration and admin tooling.
        </li>
        <li>
          <strong>No built-in authorization server.</strong> Remote mode trusts your existing identity
          provider (Entra ID, Auth0, Okta, Keycloak…).
        </li>
        <li>
          <strong>No LLM inside the server.</strong> It never sends your data anywhere except back to the
          client that asked.
        </li>
      </ul>
    </DocsShell>
  );
}
