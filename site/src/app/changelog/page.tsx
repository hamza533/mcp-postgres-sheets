import { ExternalLinkIcon } from "lucide-react";
import type { Metadata } from "next";

import { DocsShell } from "@/components/docs-shell";
import { Badge } from "@/components/ui/badge";
import { loadChangelog } from "@/lib/changelog";
import { site } from "@/lib/site";

export const metadata: Metadata = { title: "Changelog" };

/** Render `code` spans in changelog bullets. */
function Inline({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("`") && p.endsWith("`") ? (
          <code key={i}>{p.slice(1, -1)}</code>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

export default function Changelog() {
  const releases = loadChangelog();
  const anchor = (v: string) => `v${v.replace(/\./g, "-")}`.toLowerCase();
  return (
    <DocsShell
      title="Changelog"
      description="Every release, newest first. Semantic versioning; tool names and schemas only break in major versions."
      toc={releases.map((r) => ({
        id: anchor(r.version),
        title: r.version === "Unreleased" ? "Unreleased" : `v${r.version}`,
      }))}
    >
      <ol className="not-prose relative space-y-10 border-l pl-6" data-testid="releases">
        {releases.map((r) => (
          <li key={r.version} id={anchor(r.version)} className="scroll-mt-24">
            <span className="bg-brand ring-background absolute -left-[5px] mt-2 size-2.5 rounded-full ring-4" />
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold tracking-tight">
                {r.version === "Unreleased" ? "Unreleased" : `v${r.version}`}
              </h2>
              {r.date ? <span className="text-muted-foreground text-sm">{r.date}</span> : null}
              {r.breaking ? (
                <Badge variant="outline" className="bg-warn-soft text-warn border-warn/30">
                  Breaking changes
                </Badge>
              ) : null}
            </div>
            {r.version !== "Unreleased" ? (
              <div className="mt-1 flex gap-4 text-sm">
                <a
                  className="text-brand inline-flex items-center gap-1"
                  href={`${site.github}/releases/tag/v${r.version}`}
                >
                  GitHub release <ExternalLinkIcon className="size-3" />
                </a>
                <a className="text-brand inline-flex items-center gap-1" href={`${site.pypi}${r.version}/`}>
                  PyPI <ExternalLinkIcon className="size-3" />
                </a>
              </div>
            ) : null}
            {r.sections.map((s) => (
              <div key={s.title} className="mt-4">
                <h3 className="text-sm font-semibold">{s.title}</h3>
                <ul className="text-muted-foreground mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6">
                  {s.items.map((item, i) => (
                    <li key={i}>
                      <Inline text={item} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </li>
        ))}
      </ol>
    </DocsShell>
  );
}
