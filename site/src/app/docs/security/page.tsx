import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { Callout } from "@/components/callout";
import { Pill } from "@/components/pill";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { results } from "@/lib/data";

export const metadata: Metadata = { title: "Security model" };

const toc = [
  { id: "five-layers", title: "Five layers" },
  { id: "what-is-blocked", title: "What is blocked" },
  { id: "all-safety-cases", title: "All safety cases", level: 3 as const },
  { id: "audit-log", title: "Audit log" },
  { id: "what-it-does-not-do", title: "What it does not do" },
];

const layers = [
  [
    "OAuth scopes",
    "remote only",
    "Bearer tokens from your identity provider; each tool needs db:read, sheets:read or sheets:write.",
  ],
  [
    "Allow-lists",
    "schemas, tables, sheets",
    "ALLOWED_SCHEMAS, ALLOWED_TABLES and ALLOWED_SHEET_IDS — anything else is rejected before it runs.",
  ],
  [
    "SQL check",
    "single SELECT only",
    "Parsed with sqlglot: no writes, no DDL, no multiple statements, no data-modifying CTEs, no unsafe functions.",
  ],
  [
    "Read-only transaction",
    "timeout + row limit",
    "BEGIN READ ONLY, statement_timeout (5 s) and a row cap (500) through a server-side cursor.",
  ],
  [
    "Read-only database role",
    "the main guarantee",
    "The server connects as a role that only has SELECT on the allowed schemas.",
  ],
];

const highlights: { attempt: string; id: string }[] = [
  { attempt: "DROP / UPDATE", id: "dml-drop-table" },
  { attempt: "UPDATE", id: "dml-update" },
  { attempt: "Multiple statements", id: "multi-select-drop" },
  { attempt: "Data-modifying CTE", id: "cte-delete" },
  { attempt: "pg_sleep", id: "fn-pg-sleep" },
  { attempt: "Huge result sets", id: "limit-huge-result" },
  { attempt: "Write tools in read-only mode", id: "sheets-append-read-only" },
  { attempt: "Sheets outside the allow-list", id: "sheets-read-not-allowed" },
];

const RESULT_LABEL: Record<string, string> = {
  blocked: "Blocked",
  invalid: "Blocked (invalid input)",
  timeout: "Blocked (timeout)",
  capped: "Blocked (row cap)",
  not_listed: "Blocked (tool hidden)",
  forbidden: "Blocked (scope)",
};

const AUDIT_LINE = `{"ts":"2026-11-23T11:59:35.510Z","type":"audit","request_id":"9d82398322e2423fb39c527a07afa45d",
 "caller":"57fe362a-3766-4c62-b5a1-08dd3a3d7c81","client_id":"mcp-reader","transport":"http",
 "tool":"postgres_query","args":{"sql":{"redacted":true,"sha256":"a4c442a19d3f4f0c","len":20}},
 "duration_ms":0.5,"row_count":null,"outcome":"blocked",
 "error":"Rejected: only a single SELECT is allowed (got DROP)"}`;

export default function Security() {
  const cases = results.safety.cases;
  const byId = Object.fromEntries(cases.map((c) => [c.id, c]));
  return (
    <DocsShell
      title="Security model"
      description="Defence in depth: five independent layers, each enough to stop a whole class of mistakes."
      toc={toc}
    >
      <h2 id="five-layers">Five layers</h2>
      <p>
        A request passes through every layer, top to bottom. The bottom layer alone already prevents any
        write.
      </p>
      <ol className="not-prose my-6 space-y-2" aria-label="Safety layers" data-testid="layers">
        {layers.map(([name, tag, body], i) => (
          <li
            key={name}
            className="bg-card flex flex-col gap-1 rounded-lg border p-4 sm:flex-row sm:items-center sm:gap-4"
            style={{ marginLeft: `${i * 0.5}rem`, marginRight: `${i * 0.5}rem` }}
          >
            <span className="bg-brand text-brand-foreground grid size-7 shrink-0 place-items-center rounded-full text-sm font-semibold">
              {i + 1}
            </span>
            <span className="font-semibold sm:w-60 sm:shrink-0">
              {name} <span className="text-muted-foreground block text-xs font-normal">{tag}</span>
            </span>
            <span className="text-muted-foreground text-sm">{body}</span>
          </li>
        ))}
      </ol>

      <h2 id="what-is-blocked">What is blocked</h2>
      <p>
        The safety suite sends {results.safety.total} attack and misuse attempts through a real MCP session in
        CI.{" "}
        <strong>
          {results.safety.passed}/{results.safety.total}
        </strong>{" "}
        are stopped; the build fails on any regression.
      </p>
      <div className="not-prose overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Attempt</TableHead>
              <TableHead>Example</TableHead>
              <TableHead>Result</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {highlights.map(({ attempt, id }) => {
              const c = byId[id];
              if (!c) return null;
              return (
                <TableRow key={id}>
                  <TableCell className="font-medium">{attempt}</TableCell>
                  <TableCell className="max-w-md truncate font-mono text-xs" title={c.example}>
                    {c.tool === "postgres_query" ? c.example : `${c.tool} ${c.example}`}
                  </TableCell>
                  <TableCell>
                    <Pill tone="blocked">{RESULT_LABEL[c.outcome] ?? "Blocked"}</Pill>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <h3 id="all-safety-cases">All safety cases</h3>
      <details className="rounded-lg border p-4" data-testid="all-cases">
        <summary className="cursor-pointer font-medium">Show all {cases.length} cases by category</summary>
        <div className="mt-4 space-y-4">
          {Object.entries(results.safety.byCategory).map(([category, score]) => (
            <div key={category}>
              <p className="text-sm font-semibold">
                {category}{" "}
                <span className="text-muted-foreground font-normal">
                  {score.passed}/{score.total}
                </span>
              </p>
              <ul className="mt-1 ml-0 list-none space-y-1 text-sm">
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

      <h2 id="audit-log">Audit log</h2>
      <p>
        Every tool call — including rejected, invalid and unknown-tool calls — writes exactly one JSON line.
        Argument values are replaced by a fingerprint by default (<code>REDACT_ARGS=true</code>); identifiers
        such as table and sheet IDs are kept so the log stays useful. In remote mode the caller is the
        token&apos;s subject.
      </p>
      <CodeBlock lang="json" title="audit.jsonl" code={AUDIT_LINE} />
      <Callout variant="warning" title="Write tools are invisible to the AI when READ_ONLY=true.">
        They are not registered at all, so they never appear in <code>tools/list</code> — the model can&apos;t
        be talked into calling a tool it can&apos;t see.
      </Callout>

      <h2 id="what-it-does-not-do">What it does not do</h2>
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
