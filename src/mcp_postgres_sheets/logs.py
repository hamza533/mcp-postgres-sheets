"""Structured logging: one JSON object per line, carrying the current request ID.

Used in HTTP mode by default (container platforms parse JSON lines), and anywhere with
LOG_FORMAT=json. Messages never contain secrets or row data — the code logs IDs and types only.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys

from mcp_postgres_sheets.tools._runtime import request_id_var


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": dt.datetime.fromtimestamp(record.created, dt.UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "type": "log",
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = record.exc_info[0].__name__  # type only: messages may hold data
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging(level: str, json_format: bool) -> None:
    handler = logging.StreamHandler(sys.stderr)
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
