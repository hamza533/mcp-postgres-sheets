"""Streamable HTTP transport with OAuth (implemented in M4)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_postgres_sheets.config import Settings


def run_http(mcp: FastMCP[Any], settings: Settings) -> None:
    raise NotImplementedError("remote mode arrives in M4")
