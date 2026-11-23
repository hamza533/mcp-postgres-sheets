"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { docsNav } from "@/lib/site";
import { cn } from "@/lib/utils";

export type TocItem = { id: string; title: string; level?: 2 | 3 };

function DocsSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Documentation"
      className="sticky top-20 hidden h-[calc(100vh-6rem)] w-56 shrink-0 md:block"
    >
      <p className="text-muted-foreground mb-3 px-2 text-xs font-semibold tracking-wider uppercase">
        Documentation
      </p>
      <ul className="space-y-0.5">
        {docsNav.map((item) => {
          const active = pathname === item.href || pathname === item.href.replace(/\/$/, "");
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "block rounded-md px-2 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-brand-soft text-brand font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent",
                )}
              >
                {item.title}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function OnThisPage({ toc }: { toc: TocItem[] }) {
  if (!toc.length) return null;
  return (
    <aside aria-label="On this page" className="sticky top-20 hidden h-fit w-52 shrink-0 xl:block">
      <p className="mb-3 text-sm font-semibold">On this page</p>
      <ul className="space-y-1.5 border-l text-sm">
        {toc.map((item) => (
          <li key={item.id} className={cn(item.level === 3 ? "pl-6" : "pl-3")}>
            <a href={`#${item.id}`} className="text-muted-foreground hover:text-foreground block">
              {item.title}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export function DocsShell({
  title,
  description,
  toc = [],
  children,
}: {
  title: string;
  description?: string;
  toc?: TocItem[];
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-7xl gap-10 px-4 pt-10 sm:px-6">
      <DocsSidebar />
      <main className="min-w-0 flex-1" id="content">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
          {description ? <p className="text-muted-foreground mt-3 text-lg">{description}</p> : null}
        </header>
        <div className="docs-prose">{children}</div>
      </main>
      <OnThisPage toc={toc} />
    </div>
  );
}
