import "server-only";

import { readFileSync } from "node:fs";
import path from "node:path";

export type Release = {
  version: string; // "1.0.0" or "Unreleased"
  date: string | null;
  breaking: boolean;
  sections: { title: string; items: string[] }[];
};

/** Parse the Keep-a-Changelog file (copied into src/data by scripts/export_tools.py). */
export function loadChangelog(): Release[] {
  const text = readFileSync(path.join(process.cwd(), "src", "data", "changelog.md"), "utf8");
  const releases: Release[] = [];
  let release: Release | null = null;
  let section: { title: string; items: string[] } | null = null;

  for (const raw of text.split(/\r?\n/)) {
    const head = raw.match(/^## \[([^\]]+)\](?:\s*[–-]\s*(\S+))?/);
    if (head) {
      release = { version: head[1]!, date: head[2] ?? null, breaking: false, sections: [] };
      releases.push(release);
      section = null;
      continue;
    }
    const sub = raw.match(/^### (.+)/);
    if (sub && release) {
      section = { title: sub[1]!.trim(), items: [] };
      release.sections.push(section);
      if (/breaking/i.test(section.title)) release.breaking = true;
      continue;
    }
    if (!section) continue;
    if (raw.startsWith("- ")) section.items.push(raw.slice(2).trim());
    else if (/^\s{2,}\S/.test(raw) && section.items.length)
      section.items[section.items.length - 1] += " " + raw.trim();
  }
  return releases;
}
