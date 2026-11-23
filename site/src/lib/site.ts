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

export const docsNav: NavItem[] = [
  { title: "Getting started", href: "/docs/" },
  { title: "Quick start", href: "/docs/quick-start/" },
  { title: "Configuration", href: "/docs/configuration/" },
  { title: "Security model", href: "/docs/security/" },
  { title: "Tools reference", href: "/docs/tools/" },
  { title: "Remote mode & OAuth", href: "/docs/remote/" },
  { title: "Changelog", href: "/changelog/" },
];
