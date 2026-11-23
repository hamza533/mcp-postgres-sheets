"""PostgreSQL access (safety layer 4): every statement runs in a READ ONLY transaction with a
statement timeout, a restricted search_path, and a row cap enforced through a server-side
cursor, so a huge result set is never materialised in the server.

The transaction is always rolled back; nothing this module runs can commit anything.
"""

from __future__ import annotations

import asyncio
import base64
import datetime as dt
import ipaddress
import logging
import math
import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

import psycopg
from psycopg import AsyncConnection, errors
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.errors import (
    BlockedError,
    InvalidInputError,
    SafeToolError,
    TimeoutError_,
    UnavailableError,
)

log = logging.getLogger(__name__)

MAX_CELL_CHARS = 4000
APPLICATION_NAME = "mcp-postgres-sheets"


def to_jsonable(value: Any) -> Any:
    """Convert a Postgres value to something JSON can carry without losing meaning."""
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            return str(value)
        return (
            int(value)
            if value == value.to_integral_value() and abs(value) < 2**53
            else float(value)
        )
    if isinstance(value, str):
        if len(value) > MAX_CELL_CHARS:
            return value[:MAX_CELL_CHARS] + f"…[truncated {len(value) - MAX_CELL_CHARS} chars]"
        return value
    if isinstance(value, dt.datetime | dt.date | dt.time):
        return value.isoformat()
    if isinstance(value, dt.timedelta):
        return str(value)
    if isinstance(value, uuid.UUID | ipaddress.IPv4Address | ipaddress.IPv6Address):
        return str(value)
    if isinstance(value, ipaddress.IPv4Network | ipaddress.IPv6Network):
        return str(value)
    if isinstance(value, bytes | bytearray | memoryview):
        raw = bytes(value)
        if len(raw) <= 64:
            return "base64:" + base64.b64encode(raw).decode()
        return f"<{len(raw)} bytes>"
    if isinstance(value, list | tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return str(value)


def unique_column_names(names: Sequence[str]) -> list[str]:
    """`SELECT a.id, b.id` gives two `id` columns; keep both by suffixing duplicates."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for name in names:
        if name in seen:
            seen[name] += 1
            out.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 1
            out.append(name)
    return out


def map_db_error(exc: BaseException, timeout_ms: int) -> SafeToolError:
    """Translate a driver error into a message that is useful to the AI and leaks nothing."""
    if isinstance(exc, errors.QueryCanceled):
        return TimeoutError_(
            f"Query cancelled: it ran longer than the {timeout_ms} ms limit. "
            "Add filters, aggregate, or use LIMIT."
        )
    if isinstance(exc, errors.ReadOnlySqlTransaction):
        return BlockedError("the query tried to write, but it runs in a READ ONLY transaction")
    if isinstance(exc, errors.InsufficientPrivilege):
        return BlockedError("the read-only database role is not allowed to do this")
    if isinstance(exc, PoolTimeout | psycopg.OperationalError):
        return UnavailableError("The database is not reachable right now. Try again shortly.")
    if isinstance(exc, psycopg.Error):
        diag = getattr(exc, "diag", None)
        primary = getattr(diag, "message_primary", None) if diag else None
        state = getattr(exc, "sqlstate", None) or "unknown"
        if primary:
            hint = getattr(diag, "message_hint", None)
            text = f"Database error ({state}): {primary}"
            return InvalidInputError(text + (f" Hint: {hint}" if hint else ""))
        return SafeToolError(f"Database error ({state}).")
    return SafeToolError("Unexpected error while querying the database.")


class Database:
    """A lazily-opened async connection pool for the read-only role."""

    def __init__(self, settings: Settings) -> None:
        if settings.database_url is None:
            raise ValueError("DATABASE_URL is not set")
        self._conninfo = settings.database_url.get_secret_value()
        self._schemas = list(settings.allowed_schemas)
        self.timeout_ms = settings.query_timeout_ms
        self._max_size = settings.db_pool_max_size
        self._pool: AsyncConnectionPool | None = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> AsyncConnectionPool:
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    pool = AsyncConnectionPool(
                        self._conninfo,
                        min_size=1,
                        max_size=self._max_size,
                        open=False,
                        timeout=10,
                        max_idle=300,
                        kwargs={"application_name": APPLICATION_NAME, "connect_timeout": 5},
                        check=AsyncConnectionPool.check_connection,
                    )
                    await pool.open(wait=False)
                    self._pool = pool
        return self._pool

    async def open(self) -> None:
        """Create the pool eagerly (HTTP start-up), so its workers live for the whole process."""
        await self._get_pool()

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def read_only(self) -> AsyncIterator[AsyncConnection[Any]]:
        """A connection inside `BEGIN READ ONLY` with timeout + search_path; always rolled back."""
        pool = await self._get_pool()
        async with pool.connection() as conn, conn.transaction(force_rollback=True):
            await conn.execute("SET TRANSACTION READ ONLY")
            await conn.execute(
                "SELECT set_config('statement_timeout', %s, true),"
                " set_config('idle_in_transaction_session_timeout', %s, true),"
                " set_config('search_path', %s, true)",
                (
                    f"{self.timeout_ms}ms",
                    f"{self.timeout_ms + 5000}ms",
                    ", ".join('"' + s.replace('"', '""') + '"' for s in self._schemas),
                ),
            )
            yield conn

    async def run_select(
        self, sql: str, max_rows: int
    ) -> tuple[list[str], list[tuple[Any, ...]], bool]:
        """Run an already-checked SELECT. Returns (columns, rows, truncated)."""
        try:
            async with (
                asyncio.timeout(self.timeout_ms / 1000 + 5),
                self.read_only() as conn,
                # A server-side cursor: DECLARE … CURSOR only accepts a query (another layer),
                # and FETCH pulls at most max_rows + 1 rows across the wire.
                conn.cursor(name="mcp_query") as cur,
            ):
                await cur.execute(sql)
                rows = await cur.fetchmany(max_rows + 1)
                names = [d.name for d in (cur.description or [])]
        except TimeoutError:
            raise TimeoutError_(
                f"Query cancelled: it ran longer than the {self.timeout_ms} ms limit."
            ) from None
        except psycopg.Error as exc:
            raise map_db_error(exc, self.timeout_ms) from None
        except PoolTimeout as exc:
            raise map_db_error(exc, self.timeout_ms) from None
        truncated = len(rows) > max_rows
        return names, list(rows[:max_rows]), truncated

    async def fetch_all(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> list[tuple[Any, ...]]:
        """Run one of the server's own fixed catalog queries (parameterised)."""
        try:
            async with asyncio.timeout(self.timeout_ms / 1000 + 5):
                async with self.read_only() as conn:
                    cur = await conn.execute(sql, params)
                    return list(await cur.fetchall())
        except TimeoutError:
            raise TimeoutError_("Catalog query timed out.") from None
        except (psycopg.Error, PoolTimeout) as exc:
            raise map_db_error(exc, self.timeout_ms) from None

    async def ping(self) -> None:
        """Readiness check: the pool can hand out a working read-only connection."""
        await self.fetch_all("SELECT 1")
