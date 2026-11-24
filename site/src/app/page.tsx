import {
  ArrowRightIcon,
  CheckIcon,
  ChevronDownIcon,
  DatabaseIcon,
  KeyRoundIcon,
  ScrollTextIcon,
  ShieldCheckIcon,
  ShieldXIcon,
  SparklesIcon,
} from "lucide-react";
import Link from "next/link";

import { InstallCommand } from "@/components/code-block";
import { Pill } from "@/components/pill";
import { GitHubIcon } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { results, tools } from "@/lib/data";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: ShieldCheckIcon,
    title: "Read-only by default",
    body: "Connects as a database role that can only SELECT. Sheets write tools don't even exist until you set READ_ONLY=false.",
    detail: "SET TRANSACTION READ ONLY",
    href: "/docs/security/",
  },
  {
    icon: DatabaseIcon,
    title: "Layered SQL safety",
    body: "Every query is parsed (single SELECT only), allow-listed, run in a READ ONLY transaction with a timeout and a row cap.",
    detail: "5 layers, 1 role that can't write",
    href: "/docs/security/#five-layers",
  },
  {
    icon: KeyRoundIcon,
    title: "OAuth scopes for remote use",
    body: "Remote mode validates bearer tokens from your identity provider: db:read, sheets:read and sheets:write, per tool.",
    detail: "RFC 9728 · Entra ID · Keycloak",
    href: "/docs/remote/",
  },
  {
    icon: ScrollTextIcon,
    title: "Audit every call",
    body: "One JSON line per tool call: who, which tool, redacted arguments, duration, rows and outcome. Ready for your SIEM.",
    detail: "audit.jsonl · one line per call",
    href: "/docs/security/#audit-log",
  },
];

/** Real attempts from the safety suite and the server's real answers. */
const blocked = [
  { sql: "DROP TABLE customers;", reason: "Rejected: only a single SELECT is allowed (got DROP)" },
  { sql: "SELECT pg_sleep(60);", reason: "Rejected: function pg_sleep() is not allowed" },
  {
    sql: "SELECT * FROM internal.employees;",
    reason: "Rejected: schema internal is not in ALLOWED_SCHEMAS",
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
        <span className="font-medium">AI assistant</span>
        <span className="text-muted-foreground hidden sm:inline">· connected to {site.package}</span>
        <Pill tone="read" className="ml-auto">
          read-only
        </Pill>
      </div>
      <div className="space-y-4 p-4 text-sm">
        <div className="bg-muted ml-auto w-fit max-w-[85%] rounded-lg rounded-br-sm border px-4 py-2.5">
          Who were our top 5 customers by revenue last quarter?
        </div>
        <details className="group bg-sidebar w-fit rounded-lg border px-3 py-1.5 font-mono text-xs">
          <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2">
            <CheckIcon className="text-brand size-3.5" />
            <span className="font-semibold">postgres_query</span>
            <Pill tone="read">READ</Pill>
            <span className="text-muted-foreground">42 ms · 5 rows</span>
            <ChevronDownIcon className="size-3.5 transition-transform group-open:rotate-180" />
          </summary>
          <pre className="text-muted-foreground mt-2 text-[11px] leading-5 whitespace-pre-wrap">
            {`SELECT c.full_name, sum(oi.quantity * oi.unit_price) AS revenue
FROM customers c JOIN orders o ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
WHERE o.status NOT IN ('cancelled','refunded')
  AND o.ordered_at >= date_trunc('quarter', now()) - interval '3 months'
  AND o.ordered_at <  date_trunc('quarter', now())
GROUP BY 1 ORDER BY 2 DESC LIMIT 5`}
          </pre>
        </details>
        <div className="max-w-[95%] px-1">
          <p className="mb-2">
            Here are last quarter&apos;s top customers by revenue (cancelled and refunded orders excluded):
          </p>
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-sidebar">
                <tr className="label-mono text-muted-foreground">
                  <th className="px-3 py-2 font-medium">#</th>
                  <th className="px-3 py-2 font-medium">Customer</th>
                  <th className="px-3 py-2 text-right font-medium">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {answer.map(([name, revenue], i) => (
                  <tr key={name} className="border-t">
                    <td className="text-muted-foreground px-3 py-1.5 font-mono">{i + 1}</td>
                    <td className="px-3 py-1.5">{name}</td>
                    <td className="px-3 py-1.5 text-right font-mono">{revenue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const safety = results.safety;
  const p95 = Math.ceil(results.latency.maxP95Ms / 50) * 50;
  const stats = [
    { value: `${safety.passed}/${safety.total}`, label: "misuse attempts blocked" },
    { value: String(tools.length), label: "tools" },
    { value: `p95 < ${p95} ms`, label: "per tool call" },
    { value: "5", label: "independent safety layers" },
    ...(results.tasks
      ? [
          {
            value: `${results.tasks.passed}/${results.tasks.total}`,
            label: "natural-language tasks completed",
          },
        ]
      : []),
  ];

  return (
    <main id="content" className="pb-24">
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-14 pb-14 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pt-20">
        <div>
          <Pill tone="read" className="mb-5 gap-1.5">
            <SparklesIcon className="size-3" /> MCP server · open source · read-only by default
          </Pill>
          <h1 className="text-[28px] leading-9 font-bold tracking-[-0.02em] text-balance sm:text-[44px] sm:leading-[52px] sm:tracking-[-0.025em]">
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
            <Button variant="outline" asChild>
              <a href={site.github} target="_blank" rel="noreferrer">
                <GitHubIcon className="size-4" /> View on GitHub
              </a>
            </Button>
          </div>
          <InstallCommand command="uvx mcp-postgres-sheets" className="mt-7 max-w-md" />
        </div>
        <ChatPanel />
      </section>

      <section className="mx-auto max-w-6xl px-4 sm:px-6" aria-labelledby="results">
        <h2 id="results" className="sr-only">
          Results
        </h2>
        <div
          className={cn(
            "grid divide-y rounded-lg border sm:grid-cols-2 sm:divide-y-0 lg:divide-x",
            stats.length > 4 ? "lg:grid-cols-5" : "lg:grid-cols-4",
          )}
          data-testid="results-strip"
        >
          {stats.map((s) => (
            <div key={s.label} className="p-5 text-center">
              <p className="text-2xl font-bold tracking-tight">{s.value}</p>
              <p className="label-mono text-muted-foreground mt-1 normal-case">{s.label}</p>
            </div>
          ))}
        </div>
        <p className="text-muted-foreground mt-2 text-center text-xs">
          Numbers come from the committed evaluation (<code>make eval</code>) and are regenerated in CI.
        </p>
      </section>

      <section className="mx-auto mt-20 max-w-6xl px-4 sm:px-6" aria-labelledby="features">
        <p className="label-mono text-brand">Engineering guarantees</p>
        <h2
          id="features"
          className="mt-2 text-[24px] leading-8 font-semibold tracking-[-0.015em] sm:text-[28px] sm:leading-9"
        >
          Built so the AI can read your data — and nothing else
        </h2>
        <p className="text-foreground/75 mt-2 max-w-2xl">
          Every layer assumes the one before it failed: the model, the SQL check, the transaction and the
          database role each stop a different mistake.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {features.map(({ icon: Icon, title, body, detail, href }) => (
            <Link
              key={title}
              href={href}
              className="hover:border-brand/50 group rounded-lg border p-5 shadow-[0_1px_2px_0_rgba(0,0,0,0.05)] transition-colors"
            >
              <span className="bg-brand-soft text-brand grid size-9 place-items-center rounded-md">
                <Icon className="size-5" />
              </span>
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="text-foreground/75 mt-1 text-sm leading-6">{body}</p>
              <p className="text-muted-foreground group-hover:text-brand mt-4 flex items-center gap-1.5 font-mono text-xs">
                {detail} <ArrowRightIcon className="size-3" />
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-16 max-w-6xl px-4 sm:px-6" aria-labelledby="blocked">
        <div className="bg-code border-code-border text-code-foreground rounded-lg border p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <Pill tone="blocked" className="gap-1">
                <ShieldXIcon className="size-3" /> blocked by design
              </Pill>
              <h2 id="blocked" className="mt-3 text-xl font-semibold text-white">
                The AI asks. The server refuses.
              </h2>
              <p className="mt-1 max-w-xl text-sm text-slate-400">
                Real attempts from the safety suite, with the exact message the model gets back.
              </p>
            </div>
            <span className="font-mono text-xs text-slate-400">
              {results.safety.passed}/{results.safety.total} stopped in CI
            </span>
          </div>
          <ul className="mt-6 grid gap-3 lg:grid-cols-3">
            {blocked.map((b, i) => (
              <li key={b.sql} className="border-code-border rounded-lg border bg-white/[0.03] p-4">
                <p className="label-mono text-slate-500 normal-case">AI asked</p>
                <code className="mt-1 block font-mono text-[13px] text-slate-100">{b.sql}</code>
                <p
                  className="mt-3 rounded-sm border border-red-500/30 bg-red-500/10 px-2 py-1.5 font-mono text-xs text-red-300"
                  data-testid={i === 0 ? "blocked-badge" : undefined}
                >
                  {b.reason}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mx-auto mt-16 max-w-6xl px-4 text-center sm:px-6" aria-labelledby="works-with">
        <p className="label-mono text-muted-foreground">Works with</p>
        <h2 id="works-with" className="mt-2 text-lg font-semibold">
          Every client that speaks the Model Context Protocol
        </h2>
        <ul className="mt-5 flex flex-wrap justify-center gap-2">
          {["Claude Desktop", "Claude Code", "Cursor", "ChatGPT (remote)"].map((client) => (
            <li key={client} className="bg-sidebar rounded-sm border px-3 py-1.5 text-sm">
              {client}
            </li>
          ))}
          <li className="bg-brand-soft text-brand border-brand/30 rounded-sm border px-3 py-1.5 text-sm font-medium">
            Any MCP client
          </li>
        </ul>
      </section>
    </main>
  );
}
