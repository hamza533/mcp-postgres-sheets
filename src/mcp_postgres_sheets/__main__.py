"""Command-line entry point: ``mcp-postgres-sheets`` / ``python -m mcp_postgres_sheets``.

In stdio mode stdout belongs to the MCP protocol, so everything else (logs, audit lines,
start-up errors) goes to stderr.
"""

from __future__ import annotations

import argparse
import logging
import sys

from pydantic import ValidationError


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    from mcp_postgres_sheets import __version__

    parser = argparse.ArgumentParser(
        prog="mcp-postgres-sheets",
        description="MCP server for PostgreSQL and Google Sheets: read-only by default, audited.",
        epilog="All configuration comes from environment variables (see .env.example).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        help="Override TRANSPORT (default: stdio).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from mcp_postgres_sheets.config import Settings, Transport

    try:
        overrides = {"transport": args.transport} if args.transport else {}
        settings = Settings(**overrides)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']).upper() or 'config'}: {err['msg']}"
            for err in exc.errors()
        )
        print(f"mcp-postgres-sheets: invalid configuration — {problems}", file=sys.stderr)
        sys.exit(2)

    logging.getLogger().setLevel(settings.log_level.upper())

    from mcp_postgres_sheets.server import build_server

    try:
        mcp, _ = build_server(settings)
    except ValueError as exc:  # e.g. an unreadable service-account key; message has no secrets
        print(f"mcp-postgres-sheets: invalid configuration — {exc}", file=sys.stderr)
        sys.exit(2)
    if settings.transport is Transport.STDIO:
        import anyio

        from mcp_postgres_sheets.server import run_stdio

        anyio.run(run_stdio, mcp)
    else:  # pragma: no cover - exercised by the remote-mode tests
        from mcp_postgres_sheets.http_app import run_http

        run_http(mcp, settings)


if __name__ == "__main__":
    main()
