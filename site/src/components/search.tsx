"use client";

import { FileTextIcon, SearchIcon, SettingsIcon, WrenchIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { envVars, tools } from "@/lib/data";
import { docsNav } from "@/lib/site";

export function Search() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <>
      <Button
        variant="outline"
        onClick={() => setOpen(true)}
        data-testid="search-button"
        className="text-muted-foreground bg-muted/70 hover:bg-muted h-8 w-full justify-start gap-2 rounded-sm border-transparent px-2.5 text-[13px] font-normal shadow-none sm:w-60"
      >
        <SearchIcon className="size-3.5" />
        <span className="flex-1 text-left">Search docs…</span>
        <kbd className="bg-background hidden rounded-sm border px-1.5 font-mono text-[10px] font-medium sm:inline">
          Ctrl K
        </kbd>
      </Button>
      <CommandDialog
        open={open}
        onOpenChange={setOpen}
        title="Search the docs"
        description="Pages, tools and settings"
      >
        <Command>
          <CommandInput placeholder="Search pages, tools, settings…" />
          <CommandList>
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup heading="Pages">
              {docsNav.map((item) => (
                <CommandItem key={item.href} onSelect={() => go(item.href)}>
                  <FileTextIcon /> {item.title}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="Tools">
              {tools.map((t) => (
                <CommandItem
                  key={t.name}
                  value={`${t.name} ${t.title ?? ""}`}
                  onSelect={() => go(`/docs/tools/#${t.name}`)}
                >
                  <WrenchIcon /> <span className="font-mono text-xs">{t.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="Configuration">
              {envVars.map((v) => (
                <CommandItem
                  key={v.name}
                  value={`${v.name} ${v.description}`}
                  onSelect={() => go(`/docs/configuration/#${v.name}`)}
                >
                  <SettingsIcon /> <span className="font-mono text-xs">{v.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}
