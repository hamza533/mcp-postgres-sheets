/** Numbered section heading with a green "01" badge (Security, Changelog screens). */
export function SectionHeading({
  n,
  id,
  children,
  aside,
}: {
  n: number;
  id: string;
  children: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <h2 id={id} className="flex flex-wrap items-center gap-3">
      <span
        aria-hidden="true"
        className="bg-primary text-primary-foreground grid size-6 shrink-0 place-items-center rounded-full font-mono text-[11px] font-semibold"
      >
        {String(n).padStart(2, "0")}
      </span>
      <span className="flex-1">{children}</span>
      {aside ? (
        <span className="label-mono text-muted-foreground flex items-center gap-1.5 normal-case">
          {aside}
        </span>
      ) : null}
    </h2>
  );
}
