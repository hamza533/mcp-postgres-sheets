from __future__ import annotations

import io
import json
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_postgres_sheets.audit import AuditLogger, MemoryAudit, fingerprint, redact
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.server import build_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- unit -----------------------------------------------------------------------------------


def test_redaction_keeps_identifiers_and_hides_values() -> None:
    args: dict[str, Any] = {
        "sql": "SELECT email FROM customers WHERE full_name = 'Ava Smith'",
        "table": "orders",
        "sheet_id": "abc",
        "values": [["Ava", "ava@example.com"]],
        "schema": None,
    }
    out = redact(args, enabled=True)
    assert out["table"] == "orders" and out["sheet_id"] == "abc" and out["schema"] is None
    assert out["sql"]["redacted"] is True and out["sql"]["len"] == len(args["sql"])
    assert out["values"]["items"] == 1
    assert "Ava" not in json.dumps(out)
    assert redact(args, enabled=False) == args


def test_fingerprint_is_stable() -> None:
    assert fingerprint("SELECT 1") == fingerprint("SELECT 1")
    assert fingerprint("SELECT 1")["sha256"] != fingerprint("SELECT 2")["sha256"]


def test_logger_writes_one_json_line_per_record(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "audit.jsonl"
    audit = AuditLogger(path=path, redact_args=True, transport="stdio")
    for outcome in ("ok", "blocked"):
        audit.record(
            request_id="r1",
            caller="local",
            client_id=None,
            tool="postgres_query",
            arguments={"sql": "SELECT 1"},
            duration_ms=1.234,
            row_count=1,
            outcome=outcome,
            error=None,
        )
    audit.close()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["tool"] == "postgres_query"
    assert entry["caller"] == "local"
    assert entry["duration_ms"] == 1.2
    assert entry["args"]["sql"]["redacted"] is True
    assert entry["ts"].endswith("Z")
    assert set(entry) == {
        "ts", "type", "request_id", "caller", "client_id", "transport", "tool", "args",
        "duration_ms", "row_count", "outcome", "error",
    }  # fmt: skip


def test_logger_survives_broken_stream() -> None:
    stream = io.StringIO()
    stream.close()
    AuditLogger(stream=stream).record(
        request_id="r", caller="local", client_id=None, tool="t", arguments={},
        duration_ms=0, row_count=None, outcome="ok", error=None,
    )  # fmt: skip


# --- every call produces exactly one line ------------------------------------------------------


@pytest.fixture
async def audited() -> AsyncIterator[tuple[ClientSession, MemoryAudit]]:
    settings = Settings.model_validate(
        {"database_url": os.environ.get("TEST_DATABASE_URL", ""), "query_timeout_ms": 1000}
    )
    mcp, state = build_server(settings)
    audit = MemoryAudit()
    state.audit = audit
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        yield session, audit
    assert state.db is not None
    await state.db.close()


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tool", "args", "outcome", "rows"),
    [
        ("postgres_query", {"sql": "SELECT id FROM orders LIMIT 3"}, "ok", 3),
        ("postgres_list_tables", {}, "ok", 5),
        ("postgres_query", {"sql": "DROP TABLE orders"}, "blocked", None),
        ("postgres_query", {"sql": "SELECT nope FROM orders"}, "invalid", None),
        ("postgres_query", {"sql": "SELECT 1", "max_rows": 0}, "invalid", None),
        ("postgres_query", {}, "invalid", None),
        ("postgres_describe_table", {"table": "missing"}, "not_found", None),
        (
            "postgres_query",
            {"sql": "SELECT count(*) FROM order_items a, order_items b, order_items c"},
            "timeout",
            None,
        ),
        ("sheets_append_rows", {"sheet_id": "x"}, "not_listed", None),
    ],
)
async def test_every_call_is_audited_once(
    audited: tuple[ClientSession, MemoryAudit],
    tool: str,
    args: dict[str, object],
    outcome: str,
    rows: int | None,
) -> None:
    client, audit = audited
    await client.call_tool(tool, args)
    assert len(audit.entries) == 1
    entry = audit.entries[0]
    assert entry["tool"] == tool
    assert entry["outcome"] == outcome, entry
    assert entry["row_count"] == rows
    assert entry["caller"] == "local"
    assert len(entry["request_id"]) == 32
    if "sql" in args:
        assert entry["args"]["sql"]["redacted"] is True


# --- real stdio transport ---------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.anyio
async def test_stdio_transport_end_to_end(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_postgres_sheets"],
        env={
            "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", ""),
            "AUDIT_LOG_PATH": str(audit_path),
            "PATH": os.environ.get("PATH", ""),
        },
        cwd=str(tmp_path),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        assert init.serverInfo.name == "mcp-postgres-sheets"
        tools = {t.name for t in (await session.list_tools()).tools}
        assert "postgres_query" in tools
        assert "sheets_append_rows" not in tools  # READ_ONLY defaults to true
        result = await session.call_tool(
            "postgres_query", {"sql": "SELECT count(*) AS n FROM customers"}
        )
        assert not result.isError
        assert result.structuredContent is not None
        assert result.structuredContent["rows"] == [{"n": 500}]
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert [e["tool"] for e in entries] == ["postgres_query"]
    assert entries[0]["outcome"] == "ok" and entries[0]["transport"] == "stdio"
