import "server-only";

import { createHighlighter, type Highlighter } from "shiki";

// Highlighting happens at build time (server components), so the static site ships no highlighter JS.
const LANGS = ["json", "bash", "sql", "python", "yaml", "ini", "toml", "powershell", "text"] as const;
export type Lang = (typeof LANGS)[number];

let highlighter: Promise<Highlighter> | null = null;

function getHighlighter(): Promise<Highlighter> {
  highlighter ??= createHighlighter({ themes: ["github-light", "github-dark"], langs: [...LANGS] });
  return highlighter;
}

export async function highlight(code: string, lang: Lang): Promise<string> {
  const h = await getHighlighter();
  return h.codeToHtml(code, {
    lang,
    themes: { light: "github-light", dark: "github-dark" },
    defaultColor: false,
  });
}
