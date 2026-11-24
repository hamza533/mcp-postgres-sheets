"use client";

import { CheckIcon, MessageSquareIcon } from "lucide-react";
import { useState } from "react";

/** Example prompts; clicking one copies it (Quick Start "Try it"). */
export function PromptList({ prompts }: { prompts: string[] }) {
  const [copied, setCopied] = useState<number | null>(null);

  async function copy(i: number) {
    try {
      await navigator.clipboard.writeText(prompts[i] ?? "");
      setCopied(i);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setCopied(null);
    }
  }

  return (
    <ul className="not-prose my-4 space-y-2" data-testid="prompt-list">
      {prompts.map((prompt, i) => (
        <li key={prompt}>
          <button
            type="button"
            onClick={() => copy(i)}
            className="bg-sidebar hover:border-brand/40 group flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left text-sm transition-colors"
          >
            <MessageSquareIcon className="text-brand size-4 shrink-0" />
            <span className="flex-1">&ldquo;{prompt}&rdquo;</span>
            <span className="label-mono text-muted-foreground group-hover:text-foreground flex items-center gap-1 normal-case">
              {copied === i ? (
                <>
                  <CheckIcon className="text-brand size-3" /> Copied
                </>
              ) : (
                "Click to copy"
              )}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
