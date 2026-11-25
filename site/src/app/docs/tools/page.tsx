import { ShieldCheckIcon } from "lucide-react";
import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { ToolsReference } from "@/components/tools-reference";
import { tools } from "@/lib/data";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "Tools reference" };

const tocNote = (
  <div className="bg-sidebar rounded-lg border p-3 text-xs leading-5">
    <p className="label-mono text-brand mb-1 flex items-center gap-1.5 normal-case">
      <ShieldCheckIcon className="size-3.5" /> Schema safety
    </p>
    <p className="text-muted-foreground">
      Write tools require a unique idempotency_key, so a retried call never writes twice — and they are not
      registered at all when READ_ONLY=true.
    </p>
  </div>
);

export default async function ToolsPage() {
  // Example calls are highlighted at build time and handed to the (client-side) filterable list.
  const entries = await Promise.all(
    tools.map(async (t) => {
      const call = { method: "tools/call", params: { name: t.name, arguments: t.example } };
      return [
        t.name,
        <CodeBlock
          key={t.name}
          lang="json"
          title="MCP tool call"
          className="mt-4 mb-0"
          code={JSON.stringify(call, null, 2)}
        />,
      ] as const;
    }),
  );
  return (
    <DocsShell
      title="Tools reference"
      eyebrow={`${tools.length} tools registered`}
      eyebrowNote={`server v${site.version}`}
      description="Generated from the server's own tool schemas. Every tool declares a strict JSON schema for its inputs, so clients can validate calls before they are sent."
      toc={tools.map((t) => ({ id: t.name, title: t.name }))}
      tocNote={tocNote}
    >
      <p>
        Built from a real <code>tools/list</code> call (<code>make tools-json</code>); CI fails if this page
        is out of date. Tool names and input schemas are a public API: breaking changes only happen in a major
        version.
      </p>
      <ToolsReference tools={tools} examples={Object.fromEntries(entries)} />
    </DocsShell>
  );
}
