"""MCP protocol tests for the Postgres tools, through a real client session (in memory)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.server import build_server

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[ClientSession]:
    settings = Settings.model_validate({"database_url": os.environ.get("TEST_DATABASE_URL", "")})
    mcp, state = build_server(settings)
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        yield session
    assert state.db is not None
    await state.db.close()


async def call(client: ClientSession, tool: str, **args: Any) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    text = " ".join(c.text for c in result.content if isinstance(c, TextContent))
    assert not result.isError, text
    assert result.structuredContent is not None
    return result.structuredContent


async def test_tools_are_listed_with_read_only_annotations(client: ClientSession) -> None:
    tools = {t.name: t for t in (await client.list_tools()).tools}
    assert {"postgres_list_tables", "postgres_describe_table", "postgres_query"} <= set(tools)
    for name in ("postgres_list_tables", "postgres_describe_table", "postgres_query"):
        tool = tools[name]
        assert tool.annotations is not None and tool.annotations.readOnlyHint is True
        assert tool.description and len(tool.description) > 80
        assert tool.outputSchema is not None
    assert tools["postgres_query"].inputSchema["required"] == ["sql"]


async def test_list_tables(client: ClientSession) -> None:
    data = await call(client, "postgres_list_tables")
    names = {t["name"]: t for t in data["tables"]}
    assert set(names) == {"customers", "orders", "order_items", "products", "order_totals"}
    assert names["order_totals"]["kind"] == "view"
    assert names["customers"]["estimated_rows"] == 500
    assert all(t["schema_name"] == "public" for t in data["tables"])


async def test_describe_table_has_keys_and_comments(client: ClientSession) -> None:
    data = await call(client, "postgres_describe_table", table="public.orders")
    cols = {c["name"]: c for c in data["columns"]}
    assert cols["status"]["comment"].startswith("pending, paid")
    assert data["primary_key"] == ["id"]
    assert data["foreign_keys"] == [
        {
            "columns": ["customer_id"],
            "references_table": "public.customers",
            "references_columns": ["id"],
        }
    ]
    assert data["referenced_by"][0]["references_table"] == "public.order_items"


async def test_describe_missing_table(client: ClientSession) -> None:
    result = await client.call_tool("postgres_describe_table", {"table": "nope"})
    assert result.isError
    assert "not found" in result.content[0].text  # type: ignore[union-attr]


async def test_query_returns_json_rows(client: ClientSession) -> None:
    data = await call(
        client,
        "postgres_query",
        sql="SELECT category, count(*) AS n, round(avg(unit_price), 2) AS avg_price "
        "FROM products GROUP BY category ORDER BY category",
    )
    assert data["columns"] == ["category", "n", "avg_price"]
    assert data["row_count"] == 6
    assert data["truncated"] is False
    assert isinstance(data["rows"][0]["avg_price"], float)


async def test_query_errors_help_the_ai_fix_the_sql(client: ClientSession) -> None:
    result = await client.call_tool("postgres_query", {"sql": "SELECT revenue FROM orders"})
    assert result.isError
    text = result.content[0].text  # type: ignore[union-attr]
    assert 'column "revenue" does not exist' in text
    assert "mcp_readonly" not in text and "db:5432" not in text
