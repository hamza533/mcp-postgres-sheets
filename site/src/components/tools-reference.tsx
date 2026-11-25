"use client";

import { DatabaseIcon, EyeOffIcon, SearchIcon, ShieldCheckIcon, Table2Icon } from "lucide-react";
import { useMemo, useState } from "react";

import { Pill } from "@/components/pill";
import { inputRows, type Tool } from "@/lib/data";
import { cn } from "@/lib/utils";

type Filter = "all" | "read" | "write" | "postgres" | "sheets";

const matches = (t: Tool, f: Filter) =>
  f === "all" ||
  (f === "read" && t.kind === "read") ||
  (f === "write" && t.kind === "write") ||
  (f === "postgres" && t.name.startsWith("postgres_")) ||
  (f === "sheets" && t.name.startsWith("sheets_"));

/** Tool cards. `examples` are pre-highlighted (server-rendered) code blocks keyed by tool name. */
export function ToolsReference({
  tools,
  examples,
}: {
  tools: Tool[];
  examples: Record<string, React.ReactNode>;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tools.filter(
      (t) =>
        matches(t, filter) &&
        (!q ||
          `${t.name} ${t.description} ${t.scope} ${inputRows(t)
            .map((r) => r.name)
            .join(" ")}`
            .toLowerCase()
            .includes(q)),
    );
  }, [tools, query, filter]);

  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "read", label: "Read only" },
    { id: "write", label: "Write" },
    { id: "postgres", label: "PostgreSQL" },
    { id: "sheets", label: "Google Sheets" },
  ];

  return (
    <div className="not-prose">
      <div className="bg-sidebar mb-6 rounded-lg border p-3">
        <div className="relative">
          <SearchIcon className="text-muted-foreground absolute top-2.5 left-3 size-4" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && setQuery("")}
            placeholder="Filter tools by name, parameter or scope…"
            aria-label="Filter tools"
            className="bg-background focus-visible:ring-ring/50 h-9 w-full rounded-sm border pr-12 pl-9 text-sm outline-none focus-visible:ring-2"
            data-testid="tools-filter"
          />
          <kbd className="bg-muted text-muted-foreground absolute top-2 right-2 rounded-sm border px-1.5 font-mono text-[10px]">
            ESC
          </kbd>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5" role="group" aria-label="Tool type">
          {filters.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              aria-pressed={filter === f.id}
              className={cn(
                "rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors",
                filter === f.id
                  ? "bg-primary text-primary-foreground border-transparent"
                  : "bg-background text-muted-foreground hover:text-foreground",
              )}
            >
              {f.label} ({tools.filter((t) => matches(t, f.id)).length})
            </button>
          ))}
          <span className="text-brand ml-auto flex items-center gap-1 font-mono text-[11px]">
            <ShieldCheckIcon className="size-3" /> schemas from tools/list
          </span>
        </div>
      </div>
      <div className="space-y-5">
        {shown.map((tool) => {
          const rows = inputRows(tool);
          const Icon = tool.name.startsWith("postgres_") ? DatabaseIcon : Table2Icon;
          return (
            <article
              key={tool.name}
              id={tool.name}
              className={cn(
                "bg-card scroll-mt-24 overflow-hidden rounded-lg border shadow-[0_1px_2px_0_rgba(0,0,0,0.05)]",
                tool.kind === "write" && "border-l-[3px] border-l-amber-400",
              )}
              data-testid="tool-card"
            >
              {tool.hiddenWhenReadOnly ? (
                <p className="bg-warn-soft text-warn flex items-center gap-1.5 border-b px-5 py-2 font-mono text-[11px]">
                  <EyeOffIcon className="size-3.5" /> Hidden when READ_ONLY=true · requires idempotency_key
                </p>
              ) : null}
              <div className="p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Icon className="text-muted-foreground size-4" />
                  <h3 className="font-mono text-[15px] font-semibold">{tool.name}</h3>
                  <span className="ml-auto flex gap-1.5">
                    <Pill tone={tool.kind === "read" ? "read" : "write"}>{tool.kind.toUpperCase()}</Pill>
                    <Pill tone="info">{tool.scope}</Pill>
                  </span>
                </div>
                <p className="text-foreground/75 mt-2 text-sm leading-6">{tool.description}</p>

                <p className="label-mono text-muted-foreground mt-5 mb-2">Parameters</p>
                <div className="overflow-x-auto rounded-md border">
                  <table className="w-full text-left text-[13px]">
                    <thead className="bg-sidebar border-b">
                      <tr className="label-mono text-muted-foreground">
                        <th className="px-3 py-2 font-medium">Field</th>
                        <th className="px-3 py-2 font-medium">Type</th>
                        <th className="px-3 py-2 font-medium">Requirement</th>
                        <th className="min-w-64 px-3 py-2 font-medium">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="text-muted-foreground px-3 py-2">
                            No arguments.
                          </td>
                        </tr>
                      ) : (
                        rows.map((row) => (
                          <tr key={row.name} className="border-b align-top last:border-0">
                            <td className="px-3 py-2 font-mono text-xs font-semibold">{row.name}</td>
                            <td className="text-muted-foreground px-3 py-2 font-mono text-xs">{row.type}</td>
                            <td className="px-3 py-2">
                              <Pill tone={row.required ? "read" : "info"}>
                                {row.required ? "required" : "optional"}
                              </Pill>
                            </td>
                            <td className="text-foreground/80 px-3 py-2 leading-5">{row.description}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
                {examples[tool.name]}
              </div>
            </article>
          );
        })}
        {shown.length === 0 ? <p className="text-muted-foreground text-sm">No tools match.</p> : null}
      </div>
    </div>
  );
}
