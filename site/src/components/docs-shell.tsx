"use client";

import { ArrowLeftIcon, ArrowRightIcon, ChevronRightIcon, ListIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { docsNav, docsSections, sectionOf } from "@/lib/site";
import { cn } from "@/lib/utils";

export type TocItem = { id: string; title: string; level?: 2 | 3 };
export type Fact = {
  label: string;
  value: React.ReactNode;
  /** Card style only: a caption under the value and an icon in the corner. */
  detail?: React.ReactNode;
  icon?: React.ReactNode;
};

function samePath(pathname: string, href: string) {
  return pathname === href || pathname === href.replace(/\/$/, "");
}

/** Grouped docs navigation (desktop sidebar and the mobile sheet). */
export function DocsNavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <div className="space-y-6">
      {docsSections.map((section) => (
        <div key={section.title}>
          <p className="label-mono text-muted-foreground mb-2 px-3">{section.title}</p>
          <ul className="space-y-0.5">
            {section.items.map((item) => {
              const active = !item.href.includes("#") && samePath(pathname, item.href);
              const className = cn(
                "flex h-8 items-center rounded-sm px-3 text-sm transition-colors",
                active
                  ? "bg-sidebar-primary text-sidebar-primary-foreground font-medium"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-foreground",
              );
              return (
                <li key={item.href}>
                  {item.external ? (
                    <a href={item.href} target="_blank" rel="noreferrer" className={className}>
                      {item.title}
                    </a>
                  ) : (
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={className}
                      onClick={onNavigate}
                    >
                      {item.title}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function DocsSidebar() {
  return (
    <nav
      aria-label="Documentation"
      className="bg-sidebar sticky top-14 hidden h-[calc(100vh-3.5rem)] w-[260px] shrink-0 overflow-y-auto border-r px-4 py-6 md:block"
    >
      <DocsNavList />
    </nav>
  );
}

/** Highlights the section currently in view. */
function useActiveHeading(ids: string[]) {
  const [active, setActive] = useState<string | undefined>(ids[0]);
  useEffect(() => {
    if (!ids.length || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries.find((e) => e.isIntersecting);
        if (first) setActive(first.target.id);
      },
      { rootMargin: "-64px 0px -70% 0px" },
    );
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [ids]);
  return active;
}

function OnThisPage({ toc, note }: { toc: TocItem[]; note?: React.ReactNode }) {
  const active = useActiveHeading(toc.map((t) => t.id));
  if (!toc.length && !note) return null;
  return (
    <aside
      aria-label="On this page"
      className="sticky top-14 hidden h-fit w-[240px] shrink-0 py-8 pr-6 xl:block"
    >
      {toc.length ? (
        <>
          <p className="label-mono text-muted-foreground mb-3 flex items-center gap-2">
            <ListIcon className="size-3.5" /> On this page
          </p>
          <ul className="space-y-2 text-[13px] leading-5">
            {toc.map((item) => (
              <li key={item.id} className={cn(item.level === 3 && "pl-3")}>
                <a
                  href={`#${item.id}`}
                  className={cn(
                    "block transition-colors",
                    active === item.id
                      ? "text-brand font-medium"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {item.title}
                </a>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {note ? <div className="mt-6">{note}</div> : null}
    </aside>
  );
}

function Breadcrumb({ title }: { title: string }) {
  const pathname = usePathname();
  const href = docsNav.find((i) => samePath(pathname, i.href))?.href ?? pathname;
  const section = sectionOf(href);
  return (
    <nav aria-label="Breadcrumb" className="label-mono text-muted-foreground mb-3 normal-case">
      <ol className="flex flex-wrap items-center gap-1">
        <li>
          <Link href="/docs/" className="hover:text-foreground">
            Docs
          </Link>
        </li>
        {section ? (
          <li className="flex items-center gap-1">
            <ChevronRightIcon className="size-3" /> {section}
          </li>
        ) : null}
        <li className="text-brand flex items-center gap-1" aria-current="page">
          <ChevronRightIcon className="text-muted-foreground size-3" /> {title}
        </li>
      </ol>
    </nav>
  );
}

function PrevNext() {
  const pathname = usePathname();
  const index = docsNav.findIndex((i) => samePath(pathname, i.href));
  if (index < 0) return null;
  const prev = docsNav[index - 1];
  const next = docsNav[index + 1];
  return (
    <nav aria-label="Previous and next page" className="mt-16 grid gap-4 sm:grid-cols-2">
      {prev ? (
        <Link
          href={prev.href}
          className="hover:border-brand/50 rounded-lg border p-4 transition-colors"
          data-testid="prev-page"
        >
          <span className="label-mono text-muted-foreground">Previous</span>
          <span className="mt-1 flex items-center gap-2 font-semibold">
            <ArrowLeftIcon className="size-4" /> {prev.title}
          </span>
        </Link>
      ) : (
        <span />
      )}
      {next ? (
        <Link
          href={next.href}
          className="hover:border-brand/50 rounded-lg border p-4 text-right transition-colors"
          data-testid="next-page"
        >
          <span className="label-mono text-muted-foreground">Next step</span>
          <span className="text-brand mt-1 flex items-center justify-end gap-2 font-semibold">
            {next.title} <ArrowRightIcon className="size-4" />
          </span>
        </Link>
      ) : null}
    </nav>
  );
}

export function DocsShell({
  title,
  description,
  eyebrow,
  eyebrowNote,
  titleBadge,
  facts,
  factStyle = "strip",
  headerExtra,
  toc = [],
  tocNote,
  children,
}: {
  title: string;
  description?: string;
  /** Small green pill above the title, e.g. "5-minute setup". */
  eyebrow?: string;
  /** Muted text next to the eyebrow pill. */
  eyebrowNote?: React.ReactNode;
  /** Small pill after the title, e.g. "System env". */
  titleBadge?: string;
  /** Key facts under the description: one strip (Quick Start) or separate cards (Security). */
  facts?: Fact[];
  factStyle?: "strip" | "cards";
  /** Anything else under the title block (link chips…). */
  headerExtra?: React.ReactNode;
  toc?: TocItem[];
  /** A callout shown under "On this page" on wide screens. */
  tocNote?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex">
      <DocsSidebar />
      <main className="min-w-0 flex-1 px-4 py-8 sm:px-6 lg:px-10" id="content">
        <div className="mx-auto max-w-[52rem]">
          <header className="mb-8">
            <Breadcrumb title={title} />
            {eyebrow || eyebrowNote ? (
              <div className="mb-3 flex flex-wrap items-center gap-2">
                {eyebrow ? (
                  <span className="bg-brand-soft text-brand border-brand/30 inline-flex h-5 items-center rounded-full border px-2 font-mono text-[11px] font-medium">
                    {eyebrow}
                  </span>
                ) : null}
                {eyebrowNote ? (
                  <span className="text-muted-foreground flex items-center gap-1 font-mono text-[11px]">
                    {eyebrowNote}
                  </span>
                ) : null}
              </div>
            ) : null}
            <h1 className="flex flex-wrap items-center gap-x-3 text-[28px] leading-9 font-bold tracking-[-0.02em] sm:text-4xl sm:leading-[44px] sm:tracking-[-0.025em]">
              {title}
              {titleBadge ? (
                <span className="bg-info-soft text-info rounded-full border px-2 py-0.5 font-mono text-[11px] leading-none font-medium tracking-normal">
                  {titleBadge}
                </span>
              ) : null}
            </h1>
            {description ? (
              <p className="text-foreground/75 mt-2 text-base leading-[26px]">{description}</p>
            ) : null}
            {facts?.length && factStyle === "cards" ? (
              <dl className="mt-6 grid gap-3 sm:grid-cols-3" data-testid="page-facts">
                {facts.map((f) => (
                  <div key={f.label} className="bg-sidebar rounded-lg border p-4">
                    <dt className="label-mono text-muted-foreground flex items-center justify-between">
                      {f.label}
                      {f.icon ? <span className="text-brand">{f.icon}</span> : null}
                    </dt>
                    <dd className="mt-2 text-xl font-semibold tracking-tight">{f.value}</dd>
                    {f.detail ? (
                      <dd className="text-muted-foreground mt-1 text-xs leading-5">{f.detail}</dd>
                    ) : null}
                  </div>
                ))}
              </dl>
            ) : facts?.length ? (
              <dl
                className="bg-sidebar mt-6 grid gap-4 rounded-lg border p-4 sm:grid-cols-3"
                data-testid="page-facts"
              >
                {facts.map((f) => (
                  <div key={f.label}>
                    <dt className="label-mono text-muted-foreground">{f.label}</dt>
                    <dd className="mt-1 font-mono text-[13px]">{f.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {headerExtra}
          </header>
          <div className="docs-prose">{children}</div>
          <PrevNext />
        </div>
      </main>
      <OnThisPage toc={toc} note={tocNote} />
    </div>
  );
}
