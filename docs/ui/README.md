# UI designs

The website was designed in Google Stitch from the brief in `STITCH_PROMPT.md`
(Stitch project: https://stitch.google.com/projects/5140006169429412810).

**Status:** the Stitch project is private, so its exports are not in this folder yet. `/site` currently
implements the same six screens from the brief with shadcn/ui defaults.

**To align with the designs:** export each Stitch screen as PNG (1920×1080) — and its HTML/code if
offered — into this folder as `01-home.png`, `02-quick-start.png`, `03-security.png`, `04-tools.png`,
`05-configuration.png`, `06-changelog.png`, then adjust spacing, typography and colours in
`site/src/app/globals.css` and the page components to match. The design tokens (colours, radius,
fonts) all live in `globals.css`.
