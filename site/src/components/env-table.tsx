"use client";

import { SearchIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { EnvVar } from "@/lib/data";

const EXAMPLES: Record<string, string> = {
  DATABASE_URL: "postgresql://mcp_readonly:…@db:5432/shop",
  ALLOWED_SCHEMAS: "public,sales",
  ALLOWED_TABLES: "orders,public.customers",
  QUERY_TIMEOUT_MS: "3000",
  MAX_ROWS: "200",
  SHEETS_BACKEND: "memory",
  GOOGLE_SERVICE_ACCOUNT_JSON: "/secrets/sa.json",
  ALLOWED_SHEET_IDS: "1AbC…,1XyZ…",
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
};

export function EnvTable({ variables }: { variables: EnvVar[] }) {
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return variables;
    return variables.filter((v) => `${v.name} ${v.description} ${v.section}`.toLowerCase().includes(q));
  }, [query, variables]);

  return (
    <div className="not-prose my-6">
      <div className="relative mb-3 max-w-sm">
        <SearchIcon className="text-muted-foreground absolute top-2.5 left-3 size-4" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter variables…"
          aria-label="Filter environment variables"
          className="pl-9"
          data-testid="env-filter"
        />
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Default</TableHead>
              <TableHead className="min-w-80">Description</TableHead>
              <TableHead>Example</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((v) => (
              <TableRow key={v.name} id={v.name} className="scroll-mt-24 align-top" data-testid="env-row">
                <TableCell className="font-mono text-xs font-semibold">{v.name}</TableCell>
                <TableCell className="font-mono text-xs">
                  {v.default || <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="text-sm whitespace-normal">
                  <span className="text-muted-foreground mr-1 text-xs">{v.section} ·</span>
                  {v.description}
                </TableCell>
                <TableCell className="text-muted-foreground font-mono text-xs">
                  {EXAMPLES[v.name] ?? ""}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-muted-foreground mt-2 text-xs">
        {rows.length} of {variables.length} variables · generated from <code>.env.example</code>
      </p>
    </div>
  );
}
