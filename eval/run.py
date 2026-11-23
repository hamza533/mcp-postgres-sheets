"""`make eval`: safety suite, natural-language task success, latency → eval/results.{json,md}.

    uv run python -m eval.run                    # everything (tasks need GEMINI_API_KEY)
    uv run python -m eval.run --only safety      # no API key needed
    uv run python -m eval.run --only latency

Sections that are not re-run keep their previous numbers in results.json.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from eval.agent import run_agent, system_prompt
from eval.llm import GeminiClient
from eval.safety import SafetyRunner, load_cases
from eval.tasks import TASKS, TaskContext
from mcp_postgres_sheets import __version__
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.server import _instructions, build_server, close_state
from mcp_postgres_sheets.sheets import MemorySheetsBackend

HERE = Path(__file__).parent
RESULTS_JSON = HERE / "results.json"
RESULTS_MD = HERE / "results.md"
SECTIONS = ("safety", "tasks", "latency")
LATENCY_RUNS = 50


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or os.environ.get(
        "TEST_DATABASE_URL", "postgresql://mcp_readonly:mcp_readonly@localhost:5544/shop"
    )


def base_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "database_url": database_url(),
        "sheets_backend": "memory",
        "allowed_sheet_ids": "demo-sales-pipeline",
    }
    values.update(overrides)
    return Settings.model_validate(values)


@asynccontextmanager
async def session_for(settings: Settings) -> AsyncIterator[tuple[ClientSession, Any]]:
    mcp, state = build_server(settings)
    state.audit = None  # the eval measures tools, not log I/O
    try:
        async with create_connected_server_and_client_session(mcp._mcp_server) as client:
            yield client, state
    finally:
        await close_state(state)


# --- 1. safety ----------------------------------------------------------------------------------


async def run_safety() -> dict[str, Any]:
    runner = SafetyRunner(
        {
            "DATABASE_URL": database_url(),
            "SHEETS_BACKEND": "memory",
            "ALLOWED_SHEET_IDS": "demo-sales-pipeline",
        }
    )
    results = []
    try:
        for case in load_cases():
            results.append(await runner.run(case))
    finally:
        await runner.aclose()
    by_cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in results:
        by_cat[r.case.category][0] += int(r.passed)
        by_cat[r.case.category][1] += 1
    return {
        "passed": sum(r.passed for r in results),
        "total": len(results),
        "outcomes": dict(Counter(r.actual for r in results)),
        "by_category": {k: {"passed": v[0], "total": v[1]} for k, v in by_cat.items()},
        "failures": [
            {
                "id": r.case.id,
                "expected": r.case.expect,
                "actual": r.actual,
                "detail": r.detail[:300],
            }
            for r in results
            if not r.passed
        ],
        "cases": [
            {
                "id": r.case.id,
                "category": r.case.category,
                "title": r.case.title,
                "outcome": r.actual,
                "passed": r.passed,
            }
            for r in results
        ],
    }


# --- 2. tasks -----------------------------------------------------------------------------------


async def run_tasks() -> dict[str, Any]:
    llm = GeminiClient.from_env()
    if llm is None:
        return {"skipped": "GEMINI_API_KEY is not set"}
    settings = base_settings(read_only=False)
    today = dt.date.today().isoformat()
    rows: list[dict[str, Any]] = []
    for task in TASKS:
        mcp, state = build_server(settings)
        state.audit = None
        sheets = state.sheets
        assert isinstance(sheets, MemorySheetsBackend)
        started = time.perf_counter()
        try:
            async with create_connected_server_and_client_session(mcp._mcp_server) as client:
                tools = (await client.list_tools()).tools
                outcome = await run_agent(
                    llm, client, tools, system_prompt(_instructions(settings), today), task.prompt
                )
            assert state.db is not None
            ctx = TaskContext(db=state.db, sheets=sheets)
            checks = [await check(ctx, outcome.answer) for check in task.checks]
            passed = outcome.error is None and all(ok for ok, _ in checks)
            detail = outcome.error or "; ".join(d for ok, d in checks if not ok)
        except Exception as exc:  # a broken task must not hide the others
            outcome, passed, detail = None, False, f"{type(exc).__name__}: {str(exc)[:200]}"
        finally:
            await close_state(state)
        rows.append(
            {
                "id": task.id,
                "category": task.category,
                "prompt": task.prompt,
                "passed": passed,
                "tool_calls": len(outcome.calls) if outcome else 0,
                "tools": [c.name for c in outcome.calls] if outcome else [],
                "failed_calls": sum(c.is_error for c in outcome.calls) if outcome else 0,
                "answer": (outcome.answer[:500] if outcome else ""),
                "detail": "" if passed else detail,
                "seconds": round(time.perf_counter() - started, 1),
            }
        )
        print(
            f"  {'PASS' if passed else 'FAIL'}  {task.id}  ({rows[-1]['tool_calls']} tool calls)",
            flush=True,
        )
    usage = llm.usage
    return {
        "model": llm.model,
        "passed": sum(r["passed"] for r in rows),
        "total": len(rows),
        "avg_tool_calls": round(statistics.mean(r["tool_calls"] for r in rows), 2),
        "llm_requests": usage.requests,
        "llm_cached_requests": usage.cached_requests,
        "prompt_tokens": usage.prompt_tokens,
        "output_tokens": usage.output_tokens,
        "tasks": rows,
    }


# --- 3. latency ---------------------------------------------------------------------------------

LATENCY_CALLS: list[tuple[str, str, dict[str, Any]]] = [
    ("postgres_list_tables", "postgres_list_tables", {}),
    ("postgres_describe_table", "postgres_describe_table", {"table": "orders"}),
    ("postgres_query", "postgres_query (count)", {"sql": "SELECT count(*) FROM orders"}),
    (
        "postgres_query",
        "postgres_query (top-5 revenue join)",
        {
            "sql": "SELECT c.full_name, sum(oi.quantity * oi.unit_price) AS revenue FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id WHERE o.status NOT IN ('cancelled', 'refunded') GROUP BY c.id, c.full_name ORDER BY revenue DESC LIMIT 5"
        },
    ),
    (
        "postgres_query",
        "postgres_query (500 rows)",
        {"sql": "SELECT * FROM order_items ORDER BY id LIMIT 500"},
    ),
    ("sheets_list_tabs", "sheets_list_tabs", {"sheet_id": "demo-sales-pipeline"}),
    (
        "sheets_read_range",
        "sheets_read_range",
        {"sheet_id": "demo-sales-pipeline", "range": "Leads"},
    ),
    (
        "sheets_find_rows",
        "sheets_find_rows",
        {"sheet_id": "demo-sales-pipeline", "tab": "Leads", "column": "Stage", "value": "Won"},
    ),
    (
        "sheets_append_rows",
        "sheets_append_rows",
        {"sheet_id": "demo-sales-pipeline", "tab": "Notes", "rows": [["2026-11-23", "latency"]]},
    ),
    (
        "sheets_update_range",
        "sheets_update_range",
        {"sheet_id": "demo-sales-pipeline", "range": "Notes!C1", "values": [["x"]]},
    ),
]


def pct(values: list[float], q: int) -> float:
    return round(statistics.quantiles(values, n=100, method="inclusive")[q - 1], 1)


async def run_latency() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    async with session_for(base_settings(read_only=False)) as (client, _):
        for tool, label, args in LATENCY_CALLS:
            samples: list[float] = []
            for i in range(LATENCY_RUNS + 3):
                call_args = dict(args)
                if tool.startswith("sheets_") and tool.endswith(("append_rows", "update_range")):
                    call_args["idempotency_key"] = f"lat-{uuid.uuid4()}"
                started = time.perf_counter()
                result = await client.call_tool(tool, call_args)
                elapsed = (time.perf_counter() - started) * 1000
                if result.isError:
                    raise RuntimeError(f"latency call {label} failed: {result.content}")
                if i >= 3:  # warm-up excluded
                    samples.append(elapsed)
            rows.append(
                {
                    "tool": tool,
                    "label": label,
                    "n": len(samples),
                    "p50_ms": pct(samples, 50),
                    "p95_ms": pct(samples, 95),
                }
            )
    return {
        "method": f"{LATENCY_RUNS} calls per tool after 3 warm-up calls, through an in-process MCP client session "
        "(includes JSON-RPC, validation, safety checks and the Postgres round trip; excludes network). "
        "Sheets timings use the in-memory backend.",
        "tools": rows,
        "max_p95_ms": max(r["p95_ms"] for r in rows),
    }


# --- report -------------------------------------------------------------------------------------


def git_commit() -> str:
    if os.environ.get("GIT_COMMIT"):
        return os.environ["GIT_COMMIT"][:12]
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def render_md(data: dict[str, Any]) -> str:
    meta = data.get("meta", {})
    lines = [
        "# Evaluation results",
        "",
        f"Generated by `make eval` on {meta.get('generated', '?')} — server v{meta.get('version', '?')}, "
        f"commit `{meta.get('commit', '?')}`, Python {meta.get('python', '?')}.",
        "",
    ]
    s = data.get("safety")
    lines += ["## 1. Safety suite", ""]
    if s:
        lines += [
            f"**{s['passed']}/{s['total']} attack and misuse attempts stopped.**",
            "",
            "| Category | Stopped |",
            "|---|---|",
        ]
        lines += [f"| {cat} | {v['passed']}/{v['total']} |" for cat, v in s["by_category"].items()]
        lines += [
            "",
            "Outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(s["outcomes"].items())) + ".",
        ]
        if s["failures"]:
            lines += [
                "",
                "Failures:",
                *[
                    f"- `{f['id']}`: expected {f['expected']}, got {f['actual']}"
                    for f in s["failures"]
                ],
            ]
    else:
        lines += ["Not run."]
    t = data.get("tasks")
    lines += ["", "## 2. Natural-language tasks", ""]
    if not t:
        lines += ["Not run."]
    elif "skipped" in t:
        lines += [f"Not run: {t['skipped']}. Set it in `.env` and run `make eval`."]
    else:
        lines += [
            f"**{t['passed']}/{t['total']} tasks completed** by `{t['model']}` with tool calling; "
            f"average **{t['avg_tool_calls']} tool calls** per task. "
            f"{t['llm_requests']} LLM requests ({t['llm_cached_requests']} from cache), "
            f"{t['prompt_tokens']:,} prompt + {t['output_tokens']:,} output tokens.",
            "",
            "| Task | Category | Result | Tool calls |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| `{r['id']}` | {r['category']} | {'✅' if r['passed'] else '❌ ' + r['detail'][:80]} | {r['tool_calls']} |"
            for r in t["tasks"]
        ]
    lat = data.get("latency")
    lines += ["", "## 3. Latency", ""]
    if lat:
        lines += [lat["method"], "", "| Tool call | p50 (ms) | p95 (ms) |", "|---|---|---|"]
        lines += [f"| {r['label']} | {r['p50_ms']} | {r['p95_ms']} |" for r in lat["tools"]]
    else:
        lines += ["Not run."]
    return "\n".join(lines) + "\n"


async def main(only: list[str]) -> int:
    data: dict[str, Any] = (
        json.loads(RESULTS_JSON.read_text(encoding="utf-8")) if RESULTS_JSON.is_file() else {}
    )
    sections = only or list(SECTIONS)
    if "safety" in sections:
        print("safety suite…", flush=True)
        data["safety"] = await run_safety()
        print(f"  {data['safety']['passed']}/{data['safety']['total']} stopped")
    if "latency" in sections:
        print("latency…", flush=True)
        data["latency"] = await run_latency()
        print(f"  max p95 {data['latency']['max_p95_ms']} ms")
    if "tasks" in sections:
        print("natural-language tasks…", flush=True)
        data["tasks"] = await run_tasks()
        if "skipped" in data["tasks"]:
            print(f"  skipped: {data['tasks']['skipped']}")
    data["meta"] = {
        "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "version": __version__,
        "commit": git_commit(),
        "python": platform.python_version(),
    }
    RESULTS_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    RESULTS_MD.write_text(render_md(data), encoding="utf-8")
    print(
        f"wrote {RESULTS_MD.relative_to(HERE.parent)} and {RESULTS_JSON.relative_to(HERE.parent)}"
    )
    safety = data.get("safety")
    return 0 if not safety or safety["passed"] == safety["total"] else 1


if __name__ == "__main__":
    from dotenv import load_dotenv  # comes with pydantic-settings

    load_dotenv()  # GEMINI_API_KEY / GEMINI_MODEL from .env; real environment variables win
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", choices=SECTIONS, default=[])
    sys.exit(asyncio.run(main(parser.parse_args().only)))
