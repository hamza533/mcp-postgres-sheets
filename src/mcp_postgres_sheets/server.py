"""Builds the FastMCP server from settings."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_postgres_sheets import __version__
from mcp_postgres_sheets.audit import AuditLogger
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.db import Database
from mcp_postgres_sheets.sheets import build_sheets_backend
from mcp_postgres_sheets.tools._runtime import GuardedFastMCP, ServerState
from mcp_postgres_sheets.tools.postgres import register_postgres_tools
from mcp_postgres_sheets.tools.sheets import register_sheets_tools

log = logging.getLogger(__name__)

SERVER_NAME = "mcp-postgres-sheets"


def _instructions(settings: Settings) -> str:
    mode = (
        "READ-ONLY mode: Google Sheets write tools are disabled."
        if settings.read_only
        else "Sheets write tools are enabled; each write needs a unique idempotency_key."
    )
    return (
        "Answers questions from a PostgreSQL database and Google Sheets, safely. "
        "For database questions: postgres_list_tables → postgres_describe_table → postgres_query "
        "(one SELECT; aggregate in SQL). For spreadsheets: sheets_list_tabs → sheets_read_range or "
        f"sheets_find_rows. {mode} Every call is audited."
    )


def build_state(settings: Settings) -> ServerState:
    db = Database(settings) if settings.database_url is not None else None
    return ServerState.from_settings(
        settings,
        db=db,
        sheets=build_sheets_backend(settings),
        audit=AuditLogger.from_settings(settings),
    )


def build_server(
    settings: Settings, state: ServerState | None = None
) -> tuple[GuardedFastMCP, ServerState]:
    state = state or build_state(settings)

    @asynccontextmanager
    async def lifespan(_: FastMCP[Any]) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if state.db is not None:
                await state.db.close()
            if state.sheets is not None:
                await state.sheets.aclose()
            if isinstance(state.audit, AuditLogger):
                state.audit.close()

    mcp = GuardedFastMCP(
        state,
        name=SERVER_NAME,
        instructions=_instructions(settings),
        website_url="https://github.com/hamza533/mcp-postgres-sheets",
        lifespan=lifespan,
        log_level=settings.log_level.upper(),
    )
    mcp._mcp_server.version = __version__

    # Only register what is configured: tools/list shows exactly what the AI can use.
    if state.db is not None:
        register_postgres_tools(mcp, state)
    if state.sheets is not None:
        register_sheets_tools(mcp, state)
    if state.db is None and state.sheets is None:
        log.warning("neither DATABASE_URL nor Google Sheets is configured: no tools are available")
    return mcp, state
