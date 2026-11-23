import { CopyButton } from "@/components/copy-button";
import { highlight, type Lang } from "@/lib/highlight";
import { cn } from "@/lib/utils";

/** A syntax-highlighted code block (highlighted at build time) with a copy button. */
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
      className={cn("bg-code relative my-4 overflow-hidden rounded-lg border", className)}
      data-testid="code-block"
    >
      <div className="flex h-9 items-center justify-between border-b px-3">
        <span className="text-muted-foreground font-mono text-xs">{title ?? lang}</span>
        <CopyButton text={code.trim()} className="-mr-2" />
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
        "bg-code flex items-center gap-3 rounded-lg border py-1.5 pr-1.5 pl-4 font-mono text-sm",
        className,
      )}
      data-testid="install-command"
    >
      <span className="text-brand select-none">$</span>
      <code className="flex-1">{command}</code>
      <CopyButton text={command} />
    </div>
  );
}
