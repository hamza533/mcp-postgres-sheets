"use client";

import { CheckIcon, CopyIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Copies `text` to the clipboard. `label` shows a "Copy" caption next to the icon (code-block
 * headers); `onDark` is for the always-dark code surfaces.
 */
export function CopyButton({
  text,
  className,
  label = false,
  onDark = false,
}: {
  text: string;
  className?: string;
  label?: boolean;
  onDark?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size={label ? "sm" : "icon"}
      onClick={copy}
      aria-label={copied ? "Copied" : "Copy code"}
      data-testid="copy-button"
      data-copied={copied}
      className={cn(
        label ? "h-7 gap-1.5 rounded-sm px-2 font-mono text-[11px]" : "size-8",
        onDark
          ? "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10 hover:text-white"
          : "text-muted-foreground hover:text-foreground",
        className,
      )}
    >
      {copied ? <CheckIcon className="size-3.5 text-emerald-400" /> : <CopyIcon className="size-3.5" />}
      {label ? <span>{copied ? "Copied" : "Copy"}</span> : null}
    </Button>
  );
}
