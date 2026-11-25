import {
  ArrowLeftRightIcon,
  BellRingIcon,
  CircleCheckIcon,
  CirclePlusIcon,
  ExternalLinkIcon,
  HistoryIcon,
  PackageIcon,
  ShieldIcon,
  TagIcon,
  WrenchIcon,
  type LucideIcon,
} from "lucide-react";
import type { Metadata } from "next";

import { DocsShell } from "@/components/docs-shell";
import { Pill } from "@/components/pill";
import { GitHubIcon } from "@/components/site-header";
import { loadChangelog } from "@/lib/changelog";
import { results } from "@/lib/data";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";

export const metadata: Metadata = { title: "Changelog" };

/** Render `code` spans in changelog bullets. */
function Inline({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g);
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith("`") && p.endsWith("`") ? (
          <code key={i} className="bg-muted rounded-sm border px-1 font-mono text-[0.85em]">
            {p.slice(1, -1)}
          </code>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

const SECTION_STYLE: Record<string, { label: string; className: string; icon: LucideIcon; note: string }> = {
  Added: {
    label: "ADDED",
    className: "bg-brand-soft text-brand border-brand/30",
    icon: CirclePlusIcon,
    note: "New tools & capabilities",
  },
  Changed: {
    label: "CHANGED",
    className: "bg-info-soft text-info border-info/30",
    icon: ArrowLeftRightIcon,
    note: "Behaviour & defaults",
  },
  Security: {
    label: "SECURITY",
    className: "bg-muted text-foreground",
    icon: ShieldIcon,
    note: "Hardening",
  },
  Fixed: {
    label: "FIXED",
    className: "bg-warn-soft text-warn border-amber-300/60",
    icon: WrenchIcon,
    note: "Bug fixes",
  },
};

const tocNote = (
  <div className="bg-sidebar rounded-lg border p-4 text-xs leading-5">
    <p className="flex items-center gap-1.5 text-sm font-semibold">
      <BellRingIcon className="text-brand size-4" /> Release alerts
    </p>
    <p className="text-muted-foreground mt-1">
      Get notified when a release or a security fix ships: watch the repository for releases on GitHub.
    </p>
    <a
      href={site.github}
      target="_blank"
      rel="noreferrer"
      className="bg-primary text-primary-foreground mt-3 flex items-center justify-center gap-1.5 rounded-sm py-1.5 text-xs font-medium"
    >
      <GitHubIcon className="size-3.5" /> Watch on GitHub
    </a>
  </div>
);

export default function Changelog() {
  const releases = loadChangelog();
  const anchor = (v: string) => `v${v.replace(/\./g, "-")}`.toLowerCase();
  const name = (v: string) => (v === "Unreleased" ? "Unreleased" : `v${v}`);
  return (
    <DocsShell
      title="Changelog & Releases"
      eyebrow="semantic versioning"
      description="Every release, newest first: new tools, security hardening and breaking changes. Tool names and input schemas only break in a major version."
      headerExtra={
        <div className="mt-5 flex flex-wrap items-center gap-2 text-[13px]">
          <a
            href={`${site.github}/releases`}
            target="_blank"
            rel="noreferrer"
            className="hover:border-brand/50 flex items-center gap-1.5 rounded-sm border px-2.5 py-1"
          >
            <TagIcon className="size-3.5" /> GitHub releases
          </a>
          <a
            href={site.pypi}
            target="_blank"
            rel="noreferrer"
            className="hover:border-brand/50 flex items-center gap-1.5 rounded-sm border px-2.5 py-1"
          >
            <PackageIcon className="size-3.5" /> PyPI <Pill tone="read">v{site.version}</Pill>
          </a>
          <span className="text-muted-foreground flex items-center gap-1 font-mono text-[11px]">
            <CircleCheckIcon className="text-brand size-3" /> {results.safety.passed}/{results.safety.total}{" "}
            safety cases in CI
          </span>
        </div>
      }
      toc={releases.map((r) => ({ id: anchor(r.version), title: name(r.version) }))}
      tocNote={tocNote}
    >
      <div className="not-prose relative">
        <span aria-hidden="true" className="bg-border absolute top-3 bottom-0 left-[11px] w-px" />
        <ol className="relative space-y-10" data-testid="releases">
          {releases.map((r, index) => (
            <li key={r.version} id={anchor(r.version)} className="relative scroll-mt-24 pl-10">
              <span
                aria-hidden="true"
                className={cn(
                  "absolute top-4 left-0 grid size-6 place-items-center rounded-full",
                  index === 0
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground border",
                )}
              >
                {index === 0 ? (
                  <CircleCheckIcon className="size-3.5" />
                ) : (
                  <HistoryIcon className="size-3.5" />
                )}
              </span>
              <div className="bg-card rounded-lg border p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-semibold tracking-tight">{name(r.version)}</h2>
                  {r.version === "Unreleased" ? (
                    <span className="text-muted-foreground text-sm">— on main, not yet tagged</span>
                  ) : null}
                  <span className="ml-auto flex flex-wrap gap-1.5">
                    {index === 0 && r.version !== "Unreleased" ? <Pill tone="read">Latest</Pill> : null}
                    {r.breaking ? <Pill tone="write">Breaking changes</Pill> : null}
                    {r.version !== "Unreleased" ? (
                      <>
                        <a href={`${site.pypi}${r.version}/`} className="inline-flex">
                          <Pill tone="info">PyPI: v{r.version}</Pill>
                        </a>
                        <a href={`${site.github}/releases/tag/v${r.version}`} className="inline-flex">
                          <Pill tone="info" className="gap-1">
                            Release notes <ExternalLinkIcon className="size-3" />
                          </Pill>
                        </a>
                      </>
                    ) : null}
                  </span>
                </div>
                <p className="text-muted-foreground mt-1 font-mono text-xs">
                  {r.date ?? "Unreleased"} · {r.sections.reduce((n, s) => n + s.items.length, 0)} changes
                </p>
              </div>
              {r.sections.map((s) => {
                const style = SECTION_STYLE[s.title] ?? {
                  label: s.title.toUpperCase(),
                  className: "bg-muted text-foreground",
                  icon: CirclePlusIcon,
                  note: "",
                };
                return (
                  <div key={s.title} className="bg-card mt-3 rounded-lg border p-5">
                    <p className="flex items-center gap-2">
                      <span
                        className={cn(
                          "rounded-sm border px-1.5 py-0.5 font-mono text-[10px] font-semibold",
                          style.className,
                        )}
                      >
                        {style.label}
                      </span>
                      <span className="text-muted-foreground font-mono text-[11px]">{style.note}</span>
                    </p>
                    <ul className="mt-3 space-y-2 text-sm leading-6">
                      {s.items.map((item, i) => (
                        <li key={i} className="flex gap-2">
                          <style.icon className="text-muted-foreground mt-1 size-3.5 shrink-0" />
                          <span className="text-foreground/80">
                            <Inline text={item} />
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </li>
          ))}
        </ol>
      </div>
    </DocsShell>
  );
}
