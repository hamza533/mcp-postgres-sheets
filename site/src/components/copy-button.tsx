"use client";

import { CheckIcon, CopyIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CopyButton({ text, className }: { text: string; className?: string }) {
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
      size="icon"
      onClick={copy}
      aria-label={copied ? "Copied" : "Copy code"}
      data-testid="copy-button"
      data-copied={copied}
      className={cn("text-muted-foreground hover:text-foreground size-8", className)}
    >
      {copied ? <CheckIcon className="text-brand size-4" /> : <CopyIcon className="size-4" />}
    </Button>
  );
}
