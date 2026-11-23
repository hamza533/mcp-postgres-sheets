import type { Metadata } from "next";

import { CodeBlock } from "@/components/code-block";
import { DocsShell } from "@/components/docs-shell";
import { ToolsReference } from "@/components/tools-reference";
import { tools } from "@/lib/data";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "Tools reference" };

export default async function ToolsPage() {
  // Example calls are highlighted at build time and handed to the (client-side) filterable list.
  const entries = await Promise.all(
    tools.map(async (t) => {
      const call = { method: "tools/call", params: { name: t.name, arguments: t.example } };
      return [
        t.name,
        <CodeBlock key={t.name} lang="json" title="tools/call" code={JSON.stringify(call, null, 2)} />,
      ] as const;
    }),
  );
  return (
    <DocsShell
      title="Tools reference"
      description="Generated from the server's tool schemas."
      toc={tools.map((t) => ({ id: t.name, title: t.name }))}
    >
      <p>
        This page is built from a real <code>tools/list</code> call against v{site.version} of the server (
        <code>make tools-json</code>); CI fails if it is out of date. Tool names and input schemas are a
        public API: breaking changes only happen in a major version.
      </p>
      <ToolsReference tools={tools} examples={Object.fromEntries(entries)} />
    </DocsShell>
  );
}
