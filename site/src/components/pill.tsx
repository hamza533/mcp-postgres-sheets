import { cn } from "@/lib/utils";

type Tone = "read" | "write" | "blocked" | "info";

const tones: Record<Tone, string> = {
  read: "bg-brand-soft border-brand/30 text-brand",
  write: "bg-warn-soft border-amber-300/60 text-warn",
  blocked: "bg-danger-soft border-danger/30 text-danger",
  info: "bg-muted text-muted-foreground",
};

/** Mono pill badge (DESIGN.md "Badges & Tool Schema Pills"): READ / WRITE / BLOCKED / info. */
export function Pill({ tone = "info", className, ...props }: { tone?: Tone } & React.ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "inline-flex h-5 shrink-0 items-center rounded-full border px-2 font-mono text-[11px] leading-none font-medium",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
