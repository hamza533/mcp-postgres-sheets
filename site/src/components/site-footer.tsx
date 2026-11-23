import Link from "next/link";

import { site } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t">
      <div className="text-muted-foreground mx-auto flex max-w-7xl flex-col gap-4 px-4 py-10 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>
          {site.name} is open source under the{" "}
          <a
            className="hover:text-foreground underline underline-offset-4"
            href={`${site.github}/blob/main/LICENSE`}
          >
            MIT license
          </a>
          . Not affiliated with any AI vendor.
        </p>
        <nav className="flex gap-5" aria-label="Footer">
          <a className="hover:text-foreground" href={site.github} target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a className="hover:text-foreground" href={site.pypi} target="_blank" rel="noreferrer">
            PyPI
          </a>
          <Link className="hover:text-foreground" href="/docs/security/">
            Security
          </Link>
          <Link className="hover:text-foreground" href="/changelog/">
            Changelog
          </Link>
        </nav>
      </div>
    </footer>
  );
}
