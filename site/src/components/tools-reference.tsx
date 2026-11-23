"use client";

import { ChevronDownIcon, EyeOffIcon, SearchIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { inputRows, type Tool } from "@/lib/data";
import { cn } from "@/lib/utils";

type Filter = "all" | "read" | "write";

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
        (filter === "all" || t.kind === filter) &&
        (!q || `${t.name} ${t.description}`.toLowerCase().includes(q)),
    );
  }, [tools, query, filter]);

  return (
    <div className="not-prose">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-sm flex-1">
          <SearchIcon className="text-muted-foreground absolute top-2.5 left-3 size-4" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter tools…"
            aria-label="Filter tools"
            className="pl-9"
            data-testid="tools-filter"
          />
        </div>
        <div className="flex gap-1" role="group" aria-label="Tool type">
          {(["all", "read", "write"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              aria-pressed={filter === f}
              className={cn(
                "rounded-md border px-3 py-1.5 text-sm capitalize",
                filter === f ? "bg-primary text-primary-foreground" : "hover:bg-accent",
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-4">
        {shown.map((tool) => (
          <Card key={tool.name} id={tool.name} className="scroll-mt-24" data-testid="tool-card">
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="font-mono text-base">{tool.name}</CardTitle>
                <Badge
                  className={cn(
                    tool.kind === "read"
                      ? "bg-brand-soft text-brand border-brand/30"
                      : "bg-warn-soft text-warn border-warn/30",
                  )}
                  variant="outline"
                >
                  {tool.kind}
                </Badge>
                <Badge variant="secondary" className="font-mono">
                  {tool.scope}
                </Badge>
              </div>
              <CardDescription className="leading-6">{tool.description}</CardDescription>
              {tool.hiddenWhenReadOnly ? (
                <p className="text-warn flex items-center gap-1.5 text-xs font-medium">
                  <EyeOffIcon className="size-3.5" /> Hidden when READ_ONLY=true · requires idempotency_key
                </p>
              ) : null}
            </CardHeader>
            <CardContent className="space-y-3">
              <Collapsible>
                <CollapsibleTrigger className="group flex items-center gap-1.5 text-sm font-medium">
                  <ChevronDownIcon className="size-4 transition-transform group-data-[state=open]:rotate-180" />{" "}
                  Input schema
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="mt-3 overflow-x-auto rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Field</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Required</TableHead>
                          <TableHead className="min-w-72">Description</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {inputRows(tool).length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={4} className="text-muted-foreground text-sm">
                              No arguments.
                            </TableCell>
                          </TableRow>
                        ) : (
                          inputRows(tool).map((row) => (
                            <TableRow key={row.name} className="align-top">
                              <TableCell className="font-mono text-xs">{row.name}</TableCell>
                              <TableCell className="font-mono text-xs whitespace-normal">
                                {row.type}
                              </TableCell>
                              <TableCell className="text-xs">{row.required ? "yes" : "no"}</TableCell>
                              <TableCell className="text-sm whitespace-normal">{row.description}</TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </CollapsibleContent>
              </Collapsible>
              <div>
                <p className="text-sm font-medium">Example</p>
                {examples[tool.name]}
              </div>
            </CardContent>
          </Card>
        ))}
        {shown.length === 0 ? <p className="text-muted-foreground text-sm">No tools match.</p> : null}
      </div>
    </div>
  );
}
