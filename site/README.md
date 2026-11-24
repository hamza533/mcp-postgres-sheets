# Project website (`/site`)

Next.js 16 (static export) + shadcn/ui + Tailwind CSS 4. Pages: home, getting started, quick start,
configuration, security model, tools reference, remote mode & OAuth, changelog.

## Generated content — never edit by hand

`src/data/` is written by `make tools-json` (`scripts/export_tools.py`):

| File           | Source                                                        |
| -------------- | ------------------------------------------------------------- |
| `tools.json`   | a real MCP `tools/list` call against the server (all 8 tools) |
| `config.json`  | `.env.example` (names, defaults, descriptions)                |
| `results.json` | `eval/results.json` + `eval/safety_cases.json`                |
| `changelog.md` | `CHANGELOG.md`                                                |

`make lint` and the CI `site` job run `export_tools --check` and fail if any file is out of date.

## Commands

```bash
make site-setup        # npm ci
make site-dev          # http://localhost:3000
make site-check        # eslint, prettier, tsc
make site-test         # static export + Playwright smoke test (run `npx playwright install chromium` once)
```

No Node on your machine? `scripts/noded.sh npm ci`, `scripts/noded.sh npm run build`, and for Playwright
`NODED_IMAGE=mcr.microsoft.com/playwright:v1.65.1-noble scripts/noded.sh npm run test:e2e`.

## Deploy to Vercel (Hobby, free)

1. vercel.com → **Add New → Project** → import `hamza533/mcp-postgres-sheets`.
2. **Root Directory:** `site`. Framework preset: Next.js (detected). Leave build settings as in
   `vercel.json` (`npm run build`, output `out/`).
3. Deploy. Every push to `main` redeploys; pull requests get preview URLs.

`vercel.json` adds the security headers (CSP, HSTS, `X-Frame-Options: DENY`, `nosniff`, referrer and
permissions policies). The site is fully static: no serverless functions, no runtime data.

Vercel Hobby is for personal, non-commercial projects; a client deployment goes on the client's own plan
or any static host (GitHub Pages, Azure Static Web Apps, S3 + CloudFront) — upload `out/`.

## Design

Follows the Stitch design system in `docs/ui/DESIGN.md` (Inter + JetBrains Mono, slate neutrals, emerald for
read/secure, amber for writes, red for blocked, always-dark code blocks). `docs/ui/README.md` maps each
design rule to the component that implements it.
