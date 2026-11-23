# Releasing

Versions follow [SemVer](https://semver.org/). Tool names and input schemas are a public API:
removing or renaming a tool or a required argument is a **major** release.

## One-time setup (repository owner)

1. **PyPI trusted publishing** — on https://pypi.org/manage/account/publishing/ add a *pending
   publisher*: project `mcp-postgres-sheets`, owner `hamza533`, repository
   `mcp-postgres-sheets`, workflow `release.yml`, environment `pypi`. No API token is stored
   anywhere.
2. **GitHub environment** — Settings → Environments → New environment `pypi` (optionally require
   a reviewer).
3. **MCP Registry** — when you are ready to be listed, set the repository variable
   `PUBLISH_MCP_REGISTRY=true` (Settings → Secrets and variables → Actions → Variables). The
   release workflow then logs in with GitHub OIDC (namespace `io.github.hamza533/*`) and publishes
   `server.json`.
4. **Signed tags** — configure git to sign tags (`git config --global tag.gpgSign true` with a GPG
   or SSH signing key uploaded to GitHub).

## Each release

```bash
git switch main && git pull
# 1. bump the version in all three places (a test fails if they disagree)
uv version 1.1.0                     # pyproject.toml
#    src/mcp_postgres_sheets/__init__.py  __version__ = "1.1.0"
#    server.json  "version" (twice) and the ghcr.io image tag
# 2. move the [Unreleased] notes in CHANGELOG.md under "## [1.1.0] – YYYY-MM-DD"
make check eval-safety
git commit -am "chore: release 1.1.0"
git tag -s v1.1.0 -m "v1.1.0"
git push origin main v1.1.0
```

The `Release` workflow then verifies, publishes to PyPI, pushes the multi-arch image to
`ghcr.io/hamza533/mcp-postgres-sheets:1.1.0` (scanned with Trivy, with SBOM + provenance),
creates the GitHub Release from the CHANGELOG section, and (if enabled) updates the MCP Registry.
