"use client";

import { DatabaseZapIcon, MenuIcon, StarIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Search } from "@/components/search";
import { ThemeToggle } from "@/components/theme";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { docsNav, mainNav, site } from "@/lib/site";
import { cn } from "@/lib/utils";

export function Wordmark() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2 font-semibold tracking-tight"
      aria-label="PG Sheets MCP home"
    >
      <span className="bg-brand text-brand-foreground grid size-7 place-items-center rounded-md">
        <DatabaseZapIcon className="size-4" />
      </span>
      <span>{site.name}</span>
    </Link>
  );
}

function isActive(pathname: string, href: string) {
  if (href === "/docs/") return pathname === "/docs/" || pathname === "/docs";
  return pathname.startsWith(href.replace(/\/$/, ""));
}

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="bg-background/85 sticky top-0 z-40 border-b backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
              <MenuIcon className="size-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72">
            <SheetHeader>
              <SheetTitle>
                <Wordmark />
              </SheetTitle>
            </SheetHeader>
            <nav className="flex flex-col gap-1 px-4">
              {docsNav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="hover:bg-accent rounded-md px-2 py-1.5 text-sm"
                >
                  {item.title}
                </Link>
              ))}
            </nav>
          </SheetContent>
        </Sheet>
        <Wordmark />
        <Badge variant="outline" className="hidden font-mono sm:inline-flex" data-testid="version-badge">
          v{site.version}
        </Badge>
        <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="Main">
          {mainNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "hover:text-foreground rounded-md px-3 py-2 text-sm transition-colors",
                isActive(pathname, item.href) ? "text-foreground font-medium" : "text-muted-foreground",
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
              <StarIcon className="size-4" /> Star on GitHub
            </a>
          </Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
