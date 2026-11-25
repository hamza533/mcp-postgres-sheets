import {
  ArrowRightIcon,
  BanIcon,
  CircleCheckIcon,
  CodeIcon,
  DatabaseIcon,
  KeyRoundIcon,
  ScrollTextIcon,
  ShieldCheckIcon,
  ShieldXIcon,
} from "lucide-react";
import Link from "next/link";

import { InstallCommand } from "@/components/code-block";
import { DocsSidebar } from "@/components/docs-shell";
import { Pill } from "@/components/pill";
import { GitHubIcon } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { results, tools } from "@/lib/data";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: ShieldCheckIcon,
    tint: "bg-brand-soft text-brand",
    title: "Read-only by default",
    body: "Connects as a database role that can only SELECT, inside a READ ONLY transaction. Sheets write tools don't even exist until you set READ_ONLY=false.",
    detail: "SET TRANSACTION READ ONLY",
    href: "/docs/security/",
  },
  {
    icon: DatabaseIcon,
    tint: "bg-info-soft text-info",
    title: "Layered SQL safety",
    body: "Every query is parsed into a syntax tree: exactly one SELECT, allow-listed tables, no unsafe functions, then a timeout and a row cap.",
    detail: "Syntax-tree check, not regexes",
    href: "/docs/security/#five-layers",
  },
  {
    icon: KeyRoundIcon,
    tint: "bg-info-soft text-info",
    title: "OAuth scopes for remote use",
    body: "Remote mode validates bearer tokens from your identity provider: db:read, sheets:read and sheets:write, checked per tool.",
    detail: "RFC 9728 · Entra ID · Keycloak",
    href: "/docs/remote/",
  },
  {
    icon: ScrollTextIcon,
    tint: "bg-brand-soft text-brand",
    title: "Audit every call",
    body: "One JSON line per tool call: caller, tool, redacted arguments, duration, rows and outcome — ready for your log platform or SIEM.",
    detail: "audit.jsonl · one line per call",
    href: "/docs/security/#audit-log",
  },
];

/** Real attempts from the safety suite and the server's real answers. */
const blocked = [
  {
    label: "AI input attempt",
    sql: "DROP TABLE customers;",
    reason: "Rejected: only a single SELECT is allowed (got DROP)",
    violation: "DDL is refused by the syntax-tree check",
  },
  {
    label: "Stacked statement injection",
    sql: "SELECT * FROM orders; DELETE FROM orders",
    reason: "Rejected: only a single SELECT is allowed (found 2 statements)",
    violation: "More than one statement in a single call",
  },
];

const answer = [
  ["Northwind Traders", "$61,473"],
  ["Ava Patel", "$33,599"],
  ["Copperleaf Studio", "$32,360"],
  ["Kenji Chen", "$29,812"],
  ["Harbor & Pine", "$27,004"],
];

function ChatPanel() {
  return (
    <div
      className="bg-card rounded-lg border shadow-[0_4px_6px_-1px_rgba(0,0,0,0.07),0_2px_4px_-2px_rgba(0,0,0,0.05)]"
      aria-label="Example conversation with an AI assistant"
    >
      <div className="flex items-center gap-2 border-b px-4 py-3 text-sm">
        <span className="bg-brand size-2 rounded-full" />
        <span className="font-semibold">AI Assistant</span>
        <Pill tone="info" className="ml-auto gap-1">
          <span className="bg-brand size-1.5 rounded-full" /> read-only connection
        </Pill>
      </div>
      <div className="space-y-3 p-4 text-sm">
        <div className="bg-info-soft ml-auto w-fit max-w-[85%] rounded-lg rounded-br-sm px-4 py-2.5">
          Who were our top 5 customers by revenue last quarter?
        </div>
        <details className="group w-fit">
          <summary className="bg-brand-soft text-brand border-brand/30 flex cursor-pointer list-none flex-wrap items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px]">
            <CodeIcon className="size-3" />
            <span className="font-semibold">postgres_query</span>
            <span className="opacity-80">· 42 ms · 5 rows</span>
          </summary>
          <pre className="bg-sidebar text-muted-foreground mt-2 rounded-md border p-2 text-[11px] leading-5 whitespace-pre-wrap">
            {`SELECT c.full_name, sum(oi.quantity * oi.unit_price) AS revenue
FROM customers c JOIN orders o ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
WHERE o.status NOT IN ('cancelled','refunded')
  AND o.ordered_at >= date_trunc('quarter', now()) - interval '3 months'
  AND o.ordered_at <  date_trunc('quarter', now())
GROUP BY 1 ORDER BY 2 DESC LIMIT 5`}
          </pre>
        </details>
        <div className="overflow-hidden rounded-md border">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-sidebar">
              <tr className="label-mono text-muted-foreground">
                <th className="px-3 py-2 font-medium">Rank</th>
                <th className="px-3 py-2 font-medium">Customer</th>
                <th className="px-3 py-2 text-right font-medium">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {answer.map(([name, revenue], i) => (
                <tr key={name} className="border-t">
                  <td className="text-muted-foreground px-3 py-1.5 font-mono text-xs">#{i + 1}</td>
                  <td className="px-3 py-1.5">{name}</td>
                  <td className="text-brand px-3 py-1.5 text-right font-mono font-semibold">{revenue}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-foreground/80 leading-6">
          <strong>Northwind Traders</strong> was last quarter&apos;s top customer at $61,473, followed by{" "}
          <strong>Ava Patel</strong>. Cancelled and refunded orders are excluded.
        </p>
      </div>
    </div>
  );
}

export default function Home() {
  const safety = results.safety;
  const p95 = Math.ceil(results.latency.maxP95Ms / 50) * 50;
  const stats = [
    {
      value: `${safety.passed} / ${safety.total}`,
      label: "Misuse & injection attempts blocked",
      green: true,
    },
    { value: `${tools.length} tools`, label: "Postgres & Sheets primitives", green: false },
    { value: `p95 < ${p95}ms`, label: "Per tool call, measured in CI", green: true },
    ...(results.tasks
      ? [
          {
            value: `${results.tasks.passed} / ${results.tasks.total}`,
            label: "Natural-language tasks completed",
            green: false,
          },
        ]
      : [{ value: "5 layers", label: "Independent safety layers per request", green: false }]),
  ];

  return (
    <div className="flex">
      <DocsSidebar />
      <main id="content" className="min-w-0 flex-1 px-4 pb-10 sm:px-6 lg:px-10">
        <div className="mx-auto max-w-6xl">
          <section className="grid items-center gap-10 pt-12 pb-12 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
            <div>
              <span className="bg-info-soft text-foreground/80 mb-5 inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px]">
                <span className="bg-brand size-1.5 rounded-full" />v{site.version}: layered SQL safety, Google
                Sheets and OAuth scopes
              </span>
              <h1 className="text-[28px] leading-9 font-bold tracking-[-0.02em] text-balance sm:text-[40px] sm:leading-[48px] sm:tracking-[-0.025em]">
                Let your AI assistant query your data — <span className="text-brand">safely</span>
              </h1>
              <p className="text-foreground/75 mt-4 max-w-xl text-base leading-[26px]">
                An open-source MCP server for PostgreSQL and Google Sheets. Read-only by default, scoped
                permissions, full audit log.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/docs/quick-start/">
                    Get started <ArrowRightIcon className="size-4" />
                  </Link>
                </Button>
                <Button variant="secondary" asChild className="bg-info-soft hover:bg-info-soft/70">
                  <a href={site.github} target="_blank" rel="noreferrer">
                    <CodeIcon className="size-4" /> View on GitHub
                  </a>
                </Button>
              </div>
              <InstallCommand command="uvx mcp-postgres-sheets" className="mt-6 max-w-md" />
            </div>
            <ChatPanel />
          </section>

          <section aria-labelledby="results">
            <h2 id="results" className="sr-only">
              Results
            </h2>
            <div
              className={cn(
                "bg-sidebar grid gap-6 rounded-lg border p-6 sm:grid-cols-2",
                stats.length > 4 ? "lg:grid-cols-5" : "lg:grid-cols-4",
              )}
              data-testid="results-strip"
            >
              {stats.map((s) => (
                <div key={s.label} className="text-center">
                  <p
                    className={cn(
                      "text-[28px] leading-9 font-bold tracking-tight",
                      s.green ? "text-brand" : "text-foreground",
                    )}
                  >
                    {s.value}
                  </p>
                  <p className="text-muted-foreground mt-1 text-xs leading-5">{s.label}</p>
                </div>
              ))}
            </div>
            <p className="text-muted-foreground mt-2 text-center text-xs">
              Numbers come from the committed evaluation (<code>make eval</code>) and are regenerated in CI.
            </p>
          </section>

          <section className="mt-16" aria-labelledby="features">
            <p className="label-mono text-brand">Architecture guarantee</p>
            <h2
              id="features"
              className="mt-2 text-[24px] leading-8 font-semibold tracking-[-0.015em] sm:text-[28px] sm:leading-9"
            >
              Engineered for database integrity
            </h2>
            <p className="text-foreground/75 mt-2 max-w-2xl">
              A plain SQL tool hands the model an open shell. PG Sheets MCP checks every request against
              independent layers before anything touches your database.
            </p>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {features.map(({ icon: Icon, tint, title, body, detail, href }) => (
                <Link
                  key={title}
                  href={href}
                  className="bg-card hover:border-brand/50 group flex flex-col rounded-lg border p-5 shadow-[0_1px_2px_0_rgba(0,0,0,0.05)] transition-colors"
                >
                  <span className={cn("grid size-9 place-items-center rounded-md", tint)}>
                    <Icon className="size-5" />
                  </span>
                  <h3 className="mt-4 font-semibold">{title}</h3>
                  <p className="text-foreground/75 mt-1 text-sm leading-6">{body}</p>
                  <p className="text-muted-foreground group-hover:text-brand mt-auto flex items-center gap-1.5 pt-5 font-mono text-[11px] uppercase">
                    {detail} <CircleCheckIcon className="size-3" />
                  </p>
                </Link>
              ))}
            </div>
          </section>

          <section className="mt-16" aria-labelledby="blocked">
            <div className="bg-code-header border-code-border text-code-foreground rounded-lg border p-6 sm:p-8">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="inline-flex items-center gap-1 rounded-sm bg-red-500/90 px-2 py-0.5 font-mono text-[11px] font-medium text-white">
                    <ShieldXIcon className="size-3" /> Zero-trust SQL barrier
                  </span>
                  <h2 id="blocked" className="mt-3 text-2xl font-bold text-white">
                    Blocked by design
                  </h2>
                  <p className="mt-1 max-w-xl text-sm text-slate-400">
                    Real attempts from the safety suite, with the exact message the model gets back before
                    anything reaches PostgreSQL.
                  </p>
                </div>
                <span className="border-code-border rounded-sm border bg-white/5 px-2.5 py-1 font-mono text-[11px] text-slate-300">
                  {safety.passed}/{safety.total} stopped in CI
                </span>
              </div>
              <ul className="mt-6 grid gap-4 lg:grid-cols-2">
                {blocked.map((b, i) => (
                  <li key={b.sql} className="bg-code border-code-border rounded-lg border p-4">
                    <p className="flex items-center justify-between font-mono text-[11px]">
                      <span className="text-slate-400">{b.label}</span>
                      <span className="flex items-center gap-1 font-semibold text-red-400">
                        <BanIcon className="size-3" /> BLOCKED
                      </span>
                    </p>
                    <code className="mt-2 block rounded-sm bg-white/5 px-3 py-2 font-mono text-[13px] text-slate-100">
                      {b.sql}
                    </code>
                    <p
                      className="mt-3 inline-block rounded-full bg-red-500/15 px-2.5 py-1 font-mono text-[11px] text-red-300"
                      data-testid={i === 0 ? "blocked-badge" : undefined}
                    >
                      {b.reason}
                    </p>
                    <p className="mt-2 font-mono text-[11px] text-slate-400">Violation: {b.violation}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="mt-16 text-center" aria-labelledby="works-with">
            <p className="label-mono text-muted-foreground">Seamless interoperability</p>
            <h2 id="works-with" className="mt-2 text-lg font-semibold">
              Works with your favorite AI environments
            </h2>
            <ul className="mt-5 flex flex-wrap justify-center gap-2">
              {["Claude Desktop", "Claude Code", "Cursor", "ChatGPT"].map((client) => (
                <li key={client} className="bg-info-soft rounded-sm px-4 py-2 text-sm font-medium">
                  {client}
                </li>
              ))}
              <li className="bg-brand-soft text-brand rounded-sm px-4 py-2 text-sm font-medium">
                Any MCP client
              </li>
            </ul>
          </section>

          <section
            className="text-muted-foreground mt-16 flex flex-col gap-3 rounded-lg border px-4 py-3 text-xs sm:flex-row sm:items-center"
            aria-label="Project links"
          >
            <span className="flex items-center gap-2">
              <span className="text-foreground rounded-sm border px-1.5 py-0.5 font-mono text-[10px] font-semibold">
                MIT License
              </span>
              Free for commercial, local and production use.
            </span>
            <nav className="flex flex-wrap gap-4 sm:ml-auto">
              <a
                className="hover:text-foreground"
                href={`${site.github}/blob/main/docs/architecture.md`}
                target="_blank"
                rel="noreferrer"
              >
                Architecture guide
              </a>
              <Link className="hover:text-foreground" href="/docs/security/#what-is-blocked">
                Test suite ({safety.total} cases)
              </Link>
              <Link className="hover:text-foreground" href="/docs/security/">
                Security model
              </Link>
              <a
                className="hover:text-foreground flex items-center gap-1"
                href={site.github}
                target="_blank"
                rel="noreferrer"
              >
                GitHub <GitHubIcon className="size-3" />
              </a>
            </nav>
          </section>
        </div>
      </main>
    </div>
  );
}
