import { site } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="bg-sidebar border-t">
      <div className="text-muted-foreground flex flex-col gap-4 px-4 py-6 text-[13px] sm:flex-row sm:items-center sm:justify-between lg:px-6">
        <p>
          Released under the{" "}
          <a
            className="text-foreground hover:text-brand font-medium"
            href={`${site.github}/blob/main/LICENSE`}
          >
            MIT License
          </a>
          . Not affiliated with any AI vendor.
        </p>
        <nav className="flex flex-wrap items-center gap-5" aria-label="Footer">
          <a className="hover:text-foreground" href={site.github} target="_blank" rel="noreferrer">
            GitHub Repository
          </a>
          <a
            className="bg-background hover:text-foreground rounded-sm border px-1.5 py-0.5 font-mono text-[11px]"
            href={site.pypi}
            target="_blank"
            rel="noreferrer"
          >
            {site.package}
          </a>
          <a
            className="hover:text-foreground"
            href={`${site.github}/issues`}
            target="_blank"
            rel="noreferrer"
          >
            Issues &amp; Discussion
          </a>
        </nav>
      </div>
    </footer>
  );
}
