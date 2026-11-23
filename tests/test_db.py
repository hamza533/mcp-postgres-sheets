"""Defence in depth: the database layers hold even when the SQL check is bypassed."""

from __future__ import annotations

import datetime as dt
import os
import uuid
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.db import Database, to_jsonable, unique_column_names
from mcp_postgres_sheets.errors import (
    BlockedError,
    InvalidInputError,
    TimeoutError_,
    UnavailableError,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def db() -> AsyncIterator[Database]:
    database = Database(
        Settings(database_url=os.environ.get("TEST_DATABASE_URL", ""), query_timeout_ms=1000)
    )
    yield database
    await database.close()


integration = [pytest.mark.integration, pytest.mark.anyio]


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE products SET unit_price = 1",
        "DELETE FROM orders",
        "INSERT INTO products (sku, name, category, unit_price) VALUES ('Z', 'z', 'Office', 1)",
    ],
)
@pytest.mark.integration
@pytest.mark.anyio
async def test_writes_fail_even_without_the_sql_check(db: Database, sql: str) -> None:
    # Bypass sql_guard entirely: a plain (non-cursor) execute inside the READ ONLY transaction.
    with pytest.raises(BlockedError):
        await db.fetch_all(sql)


@pytest.mark.integration
@pytest.mark.anyio
async def test_role_cannot_read_unallowed_schema(db: Database) -> None:
    with pytest.raises(BlockedError, match="read-only database role"):
        await db.run_select("SELECT * FROM internal.employees", 10)


@pytest.mark.integration
@pytest.mark.anyio
async def test_declare_cursor_only_accepts_queries(db: Database) -> None:
    with pytest.raises(InvalidInputError):
        await db.run_select("DELETE FROM orders", 10)


@pytest.mark.integration
@pytest.mark.anyio
async def test_user_sql_path_rejects_multiple_statements(db: Database) -> None:
    with pytest.raises(InvalidInputError):
        await db.run_select("SELECT 1; SELECT 2", 10)


@pytest.mark.integration
@pytest.mark.anyio
async def test_statement_timeout(db: Database) -> None:
    with pytest.raises(TimeoutError_, match="1000 ms"):
        await db.run_select("SELECT pg_sleep(5)", 10)


@pytest.mark.integration
@pytest.mark.anyio
async def test_row_cap_uses_cursor(db: Database) -> None:
    names, rows, truncated = await db.run_select("SELECT g FROM generate_series(1, 100000) g", 7)
    assert names == ["g"]
    assert len(rows) == 7
    assert truncated is True


@pytest.mark.integration
@pytest.mark.anyio
async def test_timeout_cannot_be_lifted_by_role(db: Database) -> None:
    rows = await db.fetch_all(
        "SELECT current_setting('transaction_read_only'), current_setting('statement_timeout')"
    )
    assert rows == [("on", "1s")]


@pytest.mark.integration
@pytest.mark.anyio
async def test_sample_data_is_loaded(db: Database) -> None:
    rows = await db.fetch_all(
        "SELECT (SELECT count(*) FROM customers), (SELECT count(*) FROM orders), "
        "(SELECT count(*) FROM order_items), (SELECT count(*) FROM products)"
    )
    customers, orders, items, products = rows[0]
    assert (customers, orders, products) == (500, 1500, 120)
    assert customers + orders + items + products > 5000


@pytest.mark.anyio
async def test_unreachable_database_message_leaks_nothing() -> None:
    database = Database(
        Settings(database_url="postgresql://u:topsecret@127.0.0.1:1/nowhere", query_timeout_ms=500)
    )
    database._pool = None
    try:
        with pytest.raises((UnavailableError, TimeoutError_)) as info:
            await database.fetch_all("SELECT 1")
        assert "topsecret" not in str(info.value)
        assert "127.0.0.1" not in str(info.value)
    finally:
        await database.close()


def test_to_jsonable() -> None:
    assert to_jsonable(Decimal("12.50")) == 12.5
    assert to_jsonable(Decimal("42")) == 42
    assert to_jsonable(Decimal("NaN")) == "NaN"
    assert to_jsonable(dt.date(2026, 1, 2)) == "2026-01-02"
    assert (
        to_jsonable(dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.UTC)) == "2026-01-02T03:04:05+00:00"
    )
    assert to_jsonable(uuid.UUID(int=1)) == "00000000-0000-0000-0000-000000000001"
    assert to_jsonable(b"\x00\x01") == "base64:AAE="
    assert to_jsonable(b"x" * 100) == "<100 bytes>"
    assert to_jsonable("y" * 5000).endswith("[truncated 1000 chars]")
    assert to_jsonable([Decimal("1.5"), None]) == [1.5, None]
    assert to_jsonable(float("inf")) == "inf"


def test_unique_column_names() -> None:
    assert unique_column_names(["id", "id", "name", "id"]) == ["id", "id_2", "name", "id_3"]
