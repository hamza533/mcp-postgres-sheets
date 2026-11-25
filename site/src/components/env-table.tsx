"use client";

import { FilterIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Pill } from "@/components/pill";
import type { EnvVar } from "@/lib/data";
import { cn } from "@/lib/utils";

const EXAMPLES: Record<string, string> = {
  DATABASE_URL: "postgresql://mcp_readonly:…@db:5432/shop",
  ALLOWED_SCHEMAS: "public,sales",
  ALLOWED_TABLES: "orders,public.customers",
  QUERY_TIMEOUT_MS: "3000",
  MAX_ROWS: "200",
  DB_POOL_MAX_SIZE: "10",
  SHEETS_BACKEND: "memory",
  GOOGLE_SERVICE_ACCOUNT_JSON: "/secrets/sa.json",
  ALLOWED_SHEET_IDS: "1AbC…,1XyZ…",
  SHEETS_TIMEOUT_S: "20",
  READ_ONLY: "false",
  TRANSPORT: "http",
  HTTP_HOST: "0.0.0.0",
  HTTP_PORT: "8765",
  PUBLIC_URL: "https://mcp.example.com",
  OAUTH_ISSUER: "https://login.microsoftonline.com/<tenant>/v2.0",
  OAUTH_AUDIENCE: "api://mcp-postgres-sheets",
  RATE_LIMIT_PER_MIN: "120",
  AUDIT_LOG_PATH: "/var/log/mcp/audit.jsonl",
  REDACT_ARGS: "false",
  LOG_FORMAT: "json",
};

/** Settings held as secrets (SecretStr in config.py): never put them in a client config file. */
const SECRETS = new Set(["DATABASE_URL", "GOOGLE_SERVICE_ACCOUNT_JSON", "SENTRY_DSN"]);

function shortSection(section: string): string {
  if (section.startsWith("PostgreSQL")) return "Database";
  if (section.startsWith("Google Sheets")) return "Sheets";
  if (section.startsWith("OAuth")) return "OAuth";
  if (section.startsWith("Audit")) return "Audit";
  return section;
}

export function EnvTable({ variables }: { variables: EnvVar[] }) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<string | null>(null);
  const groups = useMemo(() => [...new Set(variables.map((v) => shortSection(v.section)))], [variables]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return variables.filter(
      (v) =>
        (!group || shortSection(v.section) === group) &&
        (!q || `${v.name} ${v.description} ${v.section}`.toLowerCase().includes(q)),
    );
  }, [query, group, variables]);

  const chip = (label: string, active: boolean, onClick: () => void) => (
    <button
      key={label}
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-sm px-2 py-1 font-mono text-[11px] transition-colors",
        active
          ? "bg-background text-foreground border shadow-sm"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="not-prose my-6">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative max-w-xs flex-1">
          <FilterIcon className="text-muted-foreground absolute top-2 left-2.5 size-3.5" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter variables…"
            aria-label="Filter environment variables"
            className="bg-background focus-visible:ring-ring/50 h-8 w-full rounded-sm border pr-2 pl-8 text-[13px] outline-none focus-visible:ring-2"
            data-testid="env-filter"
          />
        </div>
        <div
          className="bg-sidebar flex flex-wrap gap-0.5 rounded-md border p-0.5"
          role="group"
          aria-label="Category"
        >
          {chip(`All (${variables.length})`, group === null, () => setGroup(null))}
          {groups.map((g) => chip(g, group === g, () => setGroup(group === g ? null : g)))}
        </div>
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-left text-[13px]">
          <thead className="bg-sidebar border-b">
            <tr className="label-mono text-muted-foreground">
              <th className="px-4 py-2.5 font-medium">Variable name</th>
              <th className="px-4 py-2.5 font-medium">Default</th>
              <th className="min-w-56 px-4 py-2.5 font-medium">Description</th>
              <th className="px-4 py-2.5 font-medium">Example value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((v) => (
              <tr
                key={v.name}
                id={v.name}
                className="scroll-mt-24 border-b align-top last:border-0"
                data-testid="env-row"
              >
                <td className="px-4 py-3">
                  <span className="flex flex-wrap items-center gap-1.5 font-mono text-xs font-semibold">
                    {v.name}
                    {SECRETS.has(v.name) ? <Pill tone="write">secret</Pill> : null}
                  </span>
                  <span className="text-muted-foreground mt-0.5 block font-mono text-[10px]">
                    {shortSection(v.section)}
                  </span>
                </td>
                <td
                  className={cn(
                    "px-4 py-3 font-mono text-xs",
                    v.default === "true" ? "text-brand" : "text-muted-foreground",
                  )}
                >
                  <span className="block max-w-24 truncate" title={v.default || undefined}>
                    {v.default || "—"}
                  </span>
                </td>
                <td className="text-foreground/80 px-4 py-3 leading-5">{v.description}</td>
                <td className="px-4 py-3">
                  {EXAMPLES[v.name] ? (
                    <code
                      className="bg-info-soft block max-w-40 truncate rounded-sm px-2 py-1 font-mono text-xs"
                      title={EXAMPLES[v.name]}
                    >
                      {EXAMPLES[v.name]}
                    </code>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-muted-foreground mt-2 text-xs">
        {rows.length} of {variables.length} variables · generated from <code>.env.example</code>
      </p>
    </div>
  );
}
