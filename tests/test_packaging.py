"""Release metadata stays consistent: one version everywhere, registry name in the README."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from mcp_postgres_sheets import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_versions_match() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]
    assert __version__ == version
    assert server["version"] == version
    for package in server["packages"]:
        if package["registryType"] == "pypi":
            assert package["version"] == version
            assert package["identifier"] == pyproject["project"]["name"]
        else:
            assert package["identifier"].endswith(f":{version}")


def test_registry_ownership_marker_in_readme() -> None:
    # PyPI packages prove ownership to the MCP Registry with this marker in the README.
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"mcp-name: {server['name']}" in readme
    assert len(server["description"]) <= 100


def test_dockerfile_labels_registry_name() -> None:
    # OCI images prove ownership with this label.
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert f'io.modelcontextprotocol.server.name="{server["name"]}"' in dockerfile


def test_changelog_has_current_version_or_unreleased() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"## \[({re.escape(__version__)}|Unreleased)\]", changelog)


def test_demo_sheet_ships_in_package() -> None:
    data = ROOT / "src" / "mcp_postgres_sheets" / "data" / "sheets_demo.json"
    assert "demo-sales-pipeline" in json.loads(data.read_text(encoding="utf-8"))["spreadsheets"]


def test_every_setting_is_documented_in_env_example() -> None:
    from mcp_postgres_sheets.config import Settings

    documented = set(
        re.findall(
            r"^([A-Z][A-Z0-9_]+)=", (ROOT / ".env.example").read_text(encoding="utf-8"), re.M
        )
    )
    missing = {name.upper() for name in Settings.model_fields} - documented
    assert not missing, f"add to .env.example: {sorted(missing)}"
