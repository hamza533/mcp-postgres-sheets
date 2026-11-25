# UI designs

The website was designed in Google Stitch from the brief in `STITCH_PROMPT.md`
(Stitch project: https://stitch.google.com/projects/5140006169429412810 — private).

## What is here

| File | What it is |
|---|---|
| `DESIGN.md` | The Stitch design system ("Technical Precision"): colours, type scale, spacing, shapes and component rules. **The source of truth for the site's look.** |
| `NN-name.png` | Each screen as exported from Stitch (1280 px wide): `01-home`, `02-quick-start`, `03-security`, `04-tools`, `05-configuration`, `06-changelog`. |
| `NN-name.html` | The same screens' generated HTML (Tailwind CDN), for exact spacing and colours. |
| `STITCH_PROMPT.md` | The brief the screens were generated from. |

All six screens are exported and implemented: `/` (home), `/docs/quick-start/`, `/docs/security/`,
`/docs/tools/`, `/docs/configuration/` and `/changelog/`. The Overview (`/docs/`) and Remote pages have no
Stitch screen and use the same shell and components.

## How the site maps to the design

- Tokens (colours, radius, fonts) live in `site/src/app/globals.css`; Inter and JetBrains Mono are
  loaded in `site/src/app/layout.tsx`.
- Shell: `site-header.tsx` (56 px, translucent), `docs-shell.tsx` (260 px grouped sidebar, 832 px
  content column, numbered "On this page" rail, breadcrumb, previous/next cards).
- Components: `code-block.tsx` (always-dark code with a labelled Copy button), `callout.tsx`
  (info / warning / security / success), `pill.tsx` (READ / WRITE / BLOCKED / info badges),
  `step-heading.tsx`, `prompt-list.tsx`.
- Content is the project's real content, not the mock's placeholders (the mocks show e.g. a fake
  star count, `pg_sheets.execute_query`, `v1.0.0`, "Protocol Runtime: Healthy", "SOC2" and invented result
  payloads); where a mock shows a value, the site shows the real one or leaves it out.

To refresh a screen: export it from Stitch as `.zip` (select the screen, Export → .zip — one screen per zip) and save its
`screen.png` / `code.html` here as `NN-name.png` / `NN-name.html`.
