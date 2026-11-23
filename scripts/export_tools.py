"""Generate the website's reference data from the code, so the docs can never drift.

    uv run python -m scripts.export_tools site/src/data        # (make tools-json)
    uv run python -m scripts.export_tools site/src/data --check  # CI: fail if out of date

Writes:
  tools.json   — the result of a real MCP `tools/list` call (all 8 tools registered), plus scope,
                 read/write kind and an example call for each tool.
  config.json  — every environment variable from .env.example with its default and description.
  results.json — the headline evaluation numbers from eval/results.json (+ safety case examples).
  changelog.md — a copy of CHANGELOG.md for the changelog page.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

from mcp.shared.memory import create_connected_server_and_client_session

from mcp_postgres_sheets import __version__
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.server import build_server, close_state

ROOT = Path(__file__).resolve().parents[1]

EXAMPLES: dict[str, dict[str, Any]] = {
    "postgres_list_tables": {},
    "postgres_describe_table": {"table": "orders"},
    "postgres_query": {
        "sql": "SELECT c.full_name, sum(oi.quantity * oi.unit_price) AS revenue\nFROM customers c\nJOIN orders o ON o.customer_id = c.id\nJOIN order_items oi ON oi.order_id = o.id\nGROUP BY c.full_name\nORDER BY revenue DESC\nLIMIT 5"
    },
    "sheets_list_tabs": {"sheet_id": "1AbC…your-sheet-id"},
    "sheets_read_range": {"sheet_id": "1AbC…your-sheet-id", "range": "Leads!A1:F20"},
    "sheets_find_rows": {
        "sheet_id": "1AbC…your-sheet-id",
        "tab": "Leads",
        "column": "Stage",
        "value": "Won",
    },
    "sheets_append_rows": {
        "sheet_id": "1AbC…your-sheet-id",
        "tab": "Leads",
        "rows": [["L-1031", "Ava Chen", "Northwind Traders", "ava.chen@example.com", "New", 12000]],
        "idempotency_key": "7f3c2a9e-append-lead-1031",
    },
    "sheets_update_range": {
        "sheet_id": "1AbC…your-sheet-id",
        "range": "Leads!E5",
        "values": [["Won"]],
        "idempotency_key": "b41d0c77-mark-l1004-won",
    },
}


async def tool_list() -> list[dict[str, Any]]:
    # Register every tool: a dummy database URL (never connected) and the memory Sheets backend.
    settings = Settings.model_validate(
        {
            "database_url": "postgresql://docs:docs@127.0.0.1:1/docs",
            "sheets_backend": "memory",
            "allowed_sheet_ids": "",
            "read_only": False,
        }
    )
    mcp, state = build_server(settings)
    state.audit = None
    try:
        async with create_connected_server_and_client_session(mcp._mcp_server) as client:
            tools = (await client.list_tools()).tools
    finally:
        await close_state(state)
    out = []
    for tool in tools:
        scope = state.tool_scopes[tool.name]
        out.append(
            {
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                "kind": "write" if scope == "sheets:write" else "read",
                "scope": scope,
                "hiddenWhenReadOnly": scope == "sheets:write",
                "annotations": tool.annotations.model_dump(exclude_none=True)
                if tool.annotations
                else {},
                "inputSchema": tool.inputSchema,
                "outputSchema": tool.outputSchema,
                "example": EXAMPLES[tool.name],
            }
        )
    return out


def parse_env_example(path: Path) -> list[dict[str, str]]:
    """`# comment` lines above `NAME=value` become the variable's description."""
    variables: list[dict[str, str]] = []
    section = ""
    comments: list[str] = []
    lines = [raw.strip() for raw in path.read_text(encoding="utf-8").splitlines()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# ---"):
            # A section header is "# ---" / "# Title" / "# ---".
            if i + 2 < len(lines) and lines[i + 2].startswith("# ---"):
                section = lines[i + 1].lstrip("#").strip()
                i += 3
            else:
                i += 1
            comments = []
            continue
        i += 1
        if line.startswith("#"):
            if text := line.lstrip("#").strip():
                comments.append(text)
            continue
        match = re.match(r"^([A-Z][A-Z0-9_]+)=(.*)$", line)
        if match and not section.startswith("Evaluation"):  # eval-only keys are not server config
            name, value = match.groups()
            variables.append(
                {
                    "name": name,
                    "default": value,
                    "section": section,
                    "description": " ".join(comments),
                }
            )
        if match or not line:
            comments = []
    return variables


def _example(args: dict[str, Any]) -> str:
    if "sql" in args:
        sql = str(args["sql"])
        return sql if not sql.startswith("@@") else "SELECT 1 + SELECT 1 + … (25,000 characters)"
    shown = {
        k: ("…6,000 cells…" if isinstance(v, str) and v.startswith("@@GRID") else v)
        for k, v in args.items()
    }
    return json.dumps(shown, ensure_ascii=False)


def results_summary() -> dict[str, Any]:
    data = json.loads((ROOT / "eval" / "results.json").read_text(encoding="utf-8"))
    safety, latency, tasks = data.get("safety", {}), data.get("latency", {}), data.get("tasks", {})
    raw_cases = {
        c["id"]: c
        for c in json.loads((ROOT / "eval" / "safety_cases.json").read_text(encoding="utf-8"))[
            "cases"
        ]
    }
    cases = [
        {
            **c,
            "tool": raw_cases[c["id"]]["tool"],
            "example": _example(raw_cases[c["id"]]["args"]),
            "scopes": raw_cases[c["id"]].get("scopes"),
        }
        for c in safety.get("cases", [])
        if c["id"] in raw_cases
    ]
    return {
        "safety": {
            "passed": safety.get("passed"),
            "total": safety.get("total"),
            "byCategory": safety.get("by_category", {}),
            "cases": cases,
        },
        "latency": {"maxP95Ms": latency.get("max_p95_ms"), "tools": latency.get("tools", [])},
        "tasks": None
        if not tasks or "skipped" in tasks
        else {
            "passed": tasks["passed"],
            "total": tasks["total"],
            "avgToolCalls": tasks["avg_tool_calls"],
            "model": tasks["model"],
        },
    }


def render(out_dir: Path) -> dict[Path, str]:
    tools = asyncio.run(tool_list())
    files = {
        out_dir / "tools.json": {"version": __version__, "tools": tools},
        out_dir / "config.json": {
            "version": __version__,
            "variables": parse_env_example(ROOT / ".env.example"),
        },
        out_dir / "results.json": results_summary(),
    }
    rendered = {
        path: json.dumps(data, indent=2, ensure_ascii=False) + "\n" for path, data in files.items()
    }
    rendered[out_dir / "changelog.md"] = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed files are out of date"
    )
    args = parser.parse_args()
    stale = []
    for path, text in render(args.out_dir).items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
    if stale:
        print("out of date (run `make tools-json`): " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
