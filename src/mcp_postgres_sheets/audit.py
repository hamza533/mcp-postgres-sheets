"""Audit log: exactly one JSON line per tool call.

Fields: ts, request_id, caller, client_id, transport, tool, args, duration_ms, row_count,
outcome, error. With REDACT_ARGS=true (the default) argument *values* are replaced by a short
SHA-256 fingerprint and a length, except identifiers listed in `SAFE_ARG_KEYS` (schema, table,
sheet ID, range…), which are needed to make sense of the log and carry no row data.

In stdio mode the log goes to stderr (stdout is the protocol channel); in HTTP mode to stdout,
where a container platform (Application Insights, Cloud Logging…) collects it. AUDIT_LOG_PATH
sends it to a file instead.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import sys
import threading
from pathlib import Path
from typing import IO, Any

from mcp_postgres_sheets.config import Settings, Transport

log = logging.getLogger(__name__)

SAFE_ARG_KEYS = frozenset(
    {"schema", "table", "sheet_id", "tab", "range", "column", "max_rows", "match", "value_input"}
)


def fingerprint(value: Any) -> dict[str, Any]:
    """A stable, non-reversible stand-in for a value: lets you correlate calls without the data."""
    raw = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    shape: dict[str, Any] = {"redacted": True, "sha256": digest}
    if isinstance(value, str):
        shape["len"] = len(value)
    elif isinstance(value, list):
        shape["items"] = len(value)
    return shape


def redact(arguments: dict[str, Any], enabled: bool) -> dict[str, Any]:
    if not enabled:
        return arguments
    return {
        key: (value if key in SAFE_ARG_KEYS or value is None else fingerprint(value))
        for key, value in arguments.items()
    }


class AuditLogger:
    def __init__(
        self,
        *,
        stream: IO[str] | None = None,
        path: Path | None = None,
        redact_args: bool = True,
        transport: str = "stdio",
    ) -> None:
        self._redact = redact_args
        self._transport = transport
        self._lock = threading.Lock()
        self._path = path
        self._file: IO[str] | None = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._file = path.open("a", encoding="utf-8", buffering=1)
        self._stream = self._file or stream or sys.stderr

    @classmethod
    def from_settings(cls, settings: Settings) -> AuditLogger:
        default = sys.stderr if settings.transport is Transport.STDIO else sys.stdout
        return cls(
            stream=default,
            path=settings.audit_log_path,
            redact_args=settings.redact_args,
            transport=settings.transport.value,
        )

    def record(
        self,
        *,
        request_id: str,
        caller: str,
        client_id: str | None,
        tool: str,
        arguments: dict[str, Any],
        duration_ms: float,
        row_count: int | None,
        outcome: str,
        error: str | None,
    ) -> None:
        entry = {
            "ts": dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "type": "audit",
            "request_id": request_id,
            "caller": caller,
            "client_id": client_id,
            "transport": self._transport,
            "tool": tool,
            "args": redact(arguments, self._redact),
            "duration_ms": round(duration_ms, 1),
            "row_count": row_count,
            "outcome": outcome,
            "error": error,
        }
        line = json.dumps(entry, ensure_ascii=False, default=str, separators=(",", ":"))
        try:
            with self._lock:
                self._stream.write(line + "\n")
                self._stream.flush()
        except (OSError, ValueError):
            # Never fail the tool call because the log sink broke; say so loudly instead.
            log.error("audit log write failed for request_id=%s", request_id)

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


class MemoryAudit:
    """Collects audit entries in memory (tests and the evaluation)."""

    def __init__(self, redact_args: bool = True) -> None:
        self.entries: list[dict[str, Any]] = []
        self._redact = redact_args

    def record(self, **fields: Any) -> None:
        fields["args"] = redact(fields.pop("arguments"), self._redact)
        self.entries.append(fields)
