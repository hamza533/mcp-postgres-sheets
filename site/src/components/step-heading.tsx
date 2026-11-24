/** Numbered step heading: a small boxed number before an h2 (Quick Start steps). */
export function StepHeading({ n, id, children }: { n: number; id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className="bg-muted text-foreground grid size-6 shrink-0 place-items-center rounded-sm border font-mono text-xs font-medium"
      >
        {n}
      </span>
      <span>{children}</span>
    </h2>
  );
}
