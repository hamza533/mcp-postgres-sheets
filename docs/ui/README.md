# UI designs

The website was designed in Google Stitch from the brief in `STITCH_PROMPT.md`
(Stitch project: https://stitch.google.com/projects/5140006169429412810 — private).

## What is here

| File | What it is |
|---|---|
| `DESIGN.md` | The Stitch design system ("Technical Precision"): colours, type scale, spacing, shapes and component rules. **The source of truth for the site's look.** |
| `02-quick-start.png` | The Quick Start screen as exported from Stitch (1280 × 2570). |
| `02-quick-start.html` | The same screen's generated HTML (Tailwind CDN), for exact spacing and colours. |
| `STITCH_PROMPT.md` | The brief the screens were generated from. |

The other five screens (home, security, tools, configuration, changelog) exist in the Stitch project
but have not been exported yet; the site applies `DESIGN.md` to them, and the home page follows the
Stitch canvas thumbnail.

## How the site maps to the design

- Tokens (colours, radius, fonts) live in `site/src/app/globals.css`; Inter and JetBrains Mono are
  loaded in `site/src/app/layout.tsx`.
- Shell: `site-header.tsx` (56 px, translucent), `docs-shell.tsx` (260 px grouped sidebar, 832 px
  content column, numbered "On this page" rail, breadcrumb, previous/next cards).
- Components: `code-block.tsx` (always-dark code with a labelled Copy button), `callout.tsx`
  (info / warning / security / success), `pill.tsx` (READ / WRITE / BLOCKED / info badges),
  `step-heading.tsx`, `prompt-list.tsx`.
- Content is the project's real content, not the mock's placeholders (the mock shows e.g. a fake
  star count, `pg_sheets.execute_query` and `v1.0.0`).

To add another screen: export it from Stitch as `.zip` (select the screen, Export → .zip) and save its
`screen.png` / `code.html` here as `NN-name.png` / `NN-name.html`.
