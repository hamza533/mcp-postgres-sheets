import { BracesIcon, DatabaseIcon, FileCodeIcon, TerminalIcon } from "lucide-react";

import { CopyButton } from "@/components/copy-button";
import { highlight, type Lang } from "@/lib/highlight";
import { cn } from "@/lib/utils";

function FileIcon({ lang }: { lang: Lang }) {
  const className = "size-3.5 text-slate-400";
  if (lang === "json") return <BracesIcon className={className} />;
  if (lang === "sql") return <DatabaseIcon className={className} />;
  if (lang === "bash" || lang === "powershell") return <TerminalIcon className={className} />;
  return <FileCodeIcon className={className} />;
}

/** A syntax-highlighted code block (highlighted at build time): dark surface, file header, copy. */
export async function CodeBlock({
  code,
  lang = "text",
  title,
  className,
}: {
  code: string;
  lang?: Lang;
  title?: string;
  className?: string;
}) {
  const html = await highlight(code.trim(), lang);
  return (
    <div
      className={cn(
        "bg-code border-code-border text-code-foreground relative my-4 overflow-hidden rounded-lg border",
        className,
      )}
      data-testid="code-block"
    >
      <div className="bg-code-header border-code-border flex h-10 items-center justify-between border-b pr-2 pl-3">
        <span className="flex items-center gap-2 font-mono text-xs text-slate-300">
          <FileIcon lang={lang} />
          {title ?? lang}
        </span>
        <CopyButton text={code.trim()} label onDark />
      </div>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}

/** One-line command with a copy button (e.g. `uvx mcp-postgres-sheets`). */
export function InstallCommand({ command, className }: { command: string; className?: string }) {
  return (
    <div
      className={cn(
        "bg-code border-code-border text-code-foreground flex items-center gap-3 rounded-lg border py-1.5 pr-1.5 pl-4 font-mono text-sm",
        className,
      )}
      data-testid="install-command"
    >
      <span className="text-emerald-400 select-none">$</span>
      <code className="flex-1">{command}</code>
      <CopyButton text={command} label onDark />
    </div>
  );
}
