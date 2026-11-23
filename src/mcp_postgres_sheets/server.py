"""Builds the FastMCP server from settings."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_postgres_sheets import __version__
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.db import Database
from mcp_postgres_sheets.tools._runtime import ServerState
from mcp_postgres_sheets.tools.postgres import register_postgres_tools

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
    return ServerState.from_settings(settings, db=db)


def build_server(
    settings: Settings, state: ServerState | None = None
) -> tuple[FastMCP[Any], ServerState]:
    state = state or build_state(settings)

    @asynccontextmanager
    async def lifespan(_: FastMCP[Any]) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if state.db is not None:
                await state.db.close()

    mcp: FastMCP[Any] = FastMCP(
        name=SERVER_NAME,
        instructions=_instructions(settings),
        website_url="https://github.com/hamza533/mcp-postgres-sheets",
        lifespan=lifespan,
        log_level=settings.log_level.upper(),  # type: ignore[arg-type]
    )
    mcp._mcp_server.version = __version__

    register_postgres_tools(mcp, state)
    return mcp, state
