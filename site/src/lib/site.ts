import toolsData from "@/data/tools.json";

export const site = {
  name: "PG Sheets MCP",
  package: "mcp-postgres-sheets",
  version: toolsData.version,
  description:
    "An open-source MCP server for PostgreSQL and Google Sheets. Read-only by default, scoped permissions, full audit log.",
  github: "https://github.com/hamza533/mcp-postgres-sheets",
  pypi: "https://pypi.org/project/mcp-postgres-sheets/",
  registry: "https://registry.modelcontextprotocol.io/?q=io.github.hamza533%2Fmcp-postgres-sheets",
};

export type NavItem = { title: string; href: string };

export const mainNav: NavItem[] = [
  { title: "Docs", href: "/docs/" },
  { title: "Tools", href: "/docs/tools/" },
  { title: "Security", href: "/docs/security/" },
  { title: "Changelog", href: "/changelog/" },
];

export type NavSection = { title: string; items: (NavItem & { external?: boolean })[] };

/** The docs sidebar, grouped as in the Stitch design (docs/ui/02-quick-start.png). */
export const docsSections: NavSection[] = [
  {
    title: "Getting started",
    items: [
      { title: "Overview", href: "/docs/" },
      { title: "Quick Start", href: "/docs/quick-start/" },
    ],
  },
  {
    title: "Architecture",
    items: [
      { title: "Security Model", href: "/docs/security/" },
      { title: "Layered SQL Safety", href: "/docs/security/#five-layers" },
    ],
  },
  {
    title: "Reference",
    items: [
      { title: "Tools Reference", href: "/docs/tools/" },
      { title: "Configuration", href: "/docs/configuration/" },
    ],
  },
  { title: "Deployment", items: [{ title: "Remote Mode & OAuth", href: "/docs/remote/" }] },
  {
    title: "Project",
    items: [
      { title: "Changelog", href: "/changelog/" },
      { title: "Releases", href: `${site.github}/releases`, external: true },
    ],
  },
];

/** Docs pages in reading order (previous / next links and search). */
export const docsNav: NavItem[] = [
  { title: "Overview", href: "/docs/" },
  { title: "Quick Start", href: "/docs/quick-start/" },
  { title: "Security Model", href: "/docs/security/" },
  { title: "Tools Reference", href: "/docs/tools/" },
  { title: "Configuration", href: "/docs/configuration/" },
  { title: "Remote Mode & OAuth", href: "/docs/remote/" },
  { title: "Changelog", href: "/changelog/" },
];

/** Which sidebar group a page belongs to (breadcrumbs). */
export function sectionOf(href: string): string | undefined {
  return docsSections.find((s) => s.items.some((i) => i.href === href))?.title;
}
