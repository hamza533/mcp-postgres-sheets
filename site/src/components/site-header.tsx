"use client";

import { DatabaseZapIcon, MenuIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { DocsNavList } from "@/components/docs-shell";
import { Search } from "@/components/search";
import { ThemeToggle } from "@/components/theme";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { mainNav, site } from "@/lib/site";
import { cn } from "@/lib/utils";

export function Wordmark() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2 text-[15px] font-semibold tracking-tight"
      aria-label="PG Sheets MCP home"
    >
      <span className="bg-primary text-primary-foreground grid size-7 place-items-center rounded-md">
        <DatabaseZapIcon className="size-4" />
      </span>
      <span>{site.name}</span>
    </Link>
  );
}

/** GitHub mark (lucide no longer ships brand icons). */
export function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="currentColor">
      <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.29-1.69-1.29-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.8 1.19 1.83 1.19 3.09 0 4.42-2.7 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

function isActive(pathname: string, href: string) {
  if (href === "/docs/") return pathname === "/docs/" || pathname === "/docs";
  return pathname.startsWith(href.replace(/\/$/, ""));
}

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b bg-white/85 backdrop-blur dark:bg-[oklch(0.155_0.03_265.755/85%)]">
      <div className="flex h-14 items-center gap-3 px-4 lg:px-6">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
              <MenuIcon className="size-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 overflow-y-auto">
            <SheetHeader>
              <SheetTitle>
                <Wordmark />
              </SheetTitle>
            </SheetHeader>
            <div className="px-2 pb-6">
              <DocsNavList onNavigate={() => setOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>
        <Wordmark />
        <span
          className="bg-brand-soft text-brand border-brand/30 hidden h-5 items-center rounded-full border px-2 font-mono text-[11px] font-medium sm:inline-flex"
          data-testid="version-badge"
        >
          v{site.version}
        </span>
        <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="Main">
          {mainNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "rounded-sm px-2.5 py-1.5 text-sm transition-colors",
                isActive(pathname, item.href)
                  ? "bg-info-soft text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {item.title}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <div className="hidden sm:block">
            <Search />
          </div>
          <Button variant="outline" size="sm" asChild className="hidden gap-1.5 lg:inline-flex">
            <a href={site.github} target="_blank" rel="noreferrer">
              <GitHubIcon className="size-4" /> GitHub
            </a>
          </Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
