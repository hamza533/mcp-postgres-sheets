"""Command-line entry point: ``mcp-postgres-sheets`` / ``python -m mcp_postgres_sheets``."""

from __future__ import annotations

import sys


def main() -> None:
    from mcp_postgres_sheets import __version__

    if "--version" in sys.argv[1:]:
        print(__version__)
        return
    print("mcp-postgres-sheets: server not implemented yet (M1).", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
