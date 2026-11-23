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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { results, tools } from "@/lib/data";
import { site } from "@/lib/site";

const features = [
  {
    icon: ShieldCheckIcon,
    title: "Read-only by default",
    body: "Connects as a database role that can only SELECT. Sheets write tools don't even exist until you set READ_ONLY=false.",
  },
  {
    icon: DatabaseIcon,
    title: "Layered SQL safety",
    body: "Every query is parsed (single SELECT only), allow-listed, run in a READ ONLY transaction with a timeout and a row cap.",
  },
  {
    icon: KeyRoundIcon,
    title: "OAuth scopes for remote use",
    body: "Remote mode validates bearer tokens from your identity provider: db:read, sheets:read and sheets:write, per tool.",
  },
  {
    icon: ScrollTextIcon,
    title: "Audit every call",
    body: "One JSON line per tool call: who, which tool, redacted arguments, duration, rows and outcome. Ready for your SIEM.",
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
      className="bg-card rounded-xl border shadow-sm"
      aria-label="Example conversation with an AI assistant"
    >
      <div className="flex items-center gap-2 border-b px-4 py-3 text-sm">
        <span className="bg-brand size-2 rounded-full" />
        <span className="font-medium">AI assistant</span>
        <span className="text-muted-foreground">· connected to {site.package}</span>
      </div>
      <div className="space-y-4 p-4 text-sm">
        <div className="bg-primary text-primary-foreground ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm px-4 py-2.5">
          Who were our top 5 customers by revenue last quarter?
        </div>
        <details className="group w-fit rounded-full border px-3 py-1 font-mono text-xs open:rounded-lg">
          <summary className="flex cursor-pointer list-none items-center gap-2">
            <CheckIcon className="text-brand size-3.5" />
            postgres_query · 42 ms · 5 rows
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
        <div className="bg-muted/60 max-w-[95%] rounded-2xl rounded-bl-sm px-4 py-3">
          <p className="mb-2">
            Here are last quarter&apos;s top customers by revenue (cancelled and refunded orders excluded):
          </p>
          <table className="w-full text-left text-[13px]">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-1 font-medium">#</th>
                <th className="py-1 font-medium">Customer</th>
                <th className="py-1 text-right font-medium">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {answer.map(([name, revenue], i) => (
                <tr key={name} className="border-t">
                  <td className="py-1">{i + 1}</td>
                  <td className="py-1">{name}</td>
                  <td className="py-1 text-right font-mono">{revenue}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
    <main id="content">
      <section className="mx-auto grid max-w-7xl items-center gap-12 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-2 lg:pt-24">
        <div>
          <Badge variant="outline" className="mb-5 gap-1.5">
            <SparklesIcon className="text-brand size-3.5" /> Model Context Protocol server · open source
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Let your AI assistant query your data — <span className="text-brand">safely</span>
          </h1>
          <p className="text-muted-foreground mt-5 max-w-xl text-lg">
            An open-source MCP server for PostgreSQL and Google Sheets. Read-only by default, scoped
            permissions, full audit log.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button size="lg" asChild className="bg-brand text-brand-foreground hover:bg-brand/90">
              <Link href="/docs/quick-start/">
                Get started <ArrowRightIcon className="size-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href={site.github} target="_blank" rel="noreferrer">
                View on GitHub
              </a>
            </Button>
          </div>
          <InstallCommand command="uvx mcp-postgres-sheets" className="mt-8 max-w-md" />
        </div>
        <ChatPanel />
      </section>

      <section className="mx-auto max-w-7xl px-4 sm:px-6" aria-labelledby="features">
        <h2 id="features" className="sr-only">
          Features
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, body }) => (
            <Card key={title} className="gap-3">
              <CardHeader>
                <span className="bg-brand-soft text-brand mb-2 grid size-9 place-items-center rounded-lg">
                  <Icon className="size-5" />
                </span>
                <CardTitle className="text-base">{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="leading-6">{body}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-16 max-w-7xl px-4 sm:px-6" aria-labelledby="blocked">
        <div className="bg-card flex flex-col gap-4 rounded-xl border p-6 md:flex-row md:items-center">
          <div className="md:w-56">
            <h2 id="blocked" className="flex items-center gap-2 font-semibold">
              <ShieldXIcon className="text-destructive size-5" /> Blocked by design
            </h2>
            <p className="text-muted-foreground mt-1 text-sm">The AI asks; the server refuses.</p>
          </div>
          <code className="bg-code flex-1 rounded-md border px-4 py-3 font-mono text-sm">
            DROP TABLE customers;
          </code>
          <Badge
            variant="destructive"
            className="h-auto px-3 py-1.5 text-sm whitespace-normal"
            data-testid="blocked-badge"
          >
            Rejected: only a single SELECT is allowed
          </Badge>
        </div>
      </section>

      <section className="mx-auto mt-16 max-w-7xl px-4 text-center sm:px-6" aria-labelledby="works-with">
        <h2 id="works-with" className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
          Works with
        </h2>
        <ul className="mt-4 flex flex-wrap justify-center gap-x-10 gap-y-3 text-lg font-medium">
          {["Claude Desktop", "Claude Code", "Cursor", "ChatGPT"].map((client) => (
            <li key={client}>{client}</li>
          ))}
        </ul>
      </section>

      <section className="mx-auto mt-16 max-w-7xl px-4 sm:px-6" aria-labelledby="results">
        <h2 id="results" className="sr-only">
          Results
        </h2>
        <div
          className="bg-brand-soft grid gap-6 rounded-xl border p-8 sm:grid-cols-2 lg:grid-cols-4"
          data-testid="results-strip"
        >
          {stats.map((s) => (
            <div key={s.label}>
              <p className="text-brand text-3xl font-semibold tracking-tight">{s.value}</p>
              <p className="text-muted-foreground mt-1 text-sm">{s.label}</p>
            </div>
          ))}
        </div>
        <p className="text-muted-foreground mt-3 text-center text-xs">
          Numbers come from the committed evaluation (<code>make eval</code>) and are regenerated in CI.
        </p>
      </section>
    </main>
  );
}
