"""The single choke point every tool call goes through.

`GuardedFastMCP.call_tool` wraps FastMCP's own dispatch, so it sees *every* call — including
unknown tools and calls whose arguments fail validation — and for each one it:

1. resolves the caller (OAuth token subject in remote mode, ``local`` over stdio),
2. checks the tool's OAuth scope (remote mode),
3. applies the per-caller rate limit (remote mode),
4. runs the tool,
5. writes exactly one audit line.

`safe_errors` wraps each tool function so that only `SafeToolError` messages ever reach the AI;
any other exception is replaced with a generic message carrying a request ID.
"""

from __future__ import annotations

import contextvars
import functools
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ContentBlock, ToolAnnotations
from pydantic import ValidationError

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.errors import ForbiddenError, RateLimitedError, SafeToolError
from mcp_postgres_sheets.sql_guard import AllowList

if TYPE_CHECKING:
    from mcp_postgres_sheets.db import Database

log = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

LOCAL_CALLER = "local"

# Set by the HTTP layer from X-Request-ID (or generated) so HTTP logs and audit lines correlate.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class AuditSink(Protocol):
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
    ) -> None: ...


class Limiter(Protocol):
    def allow(self, key: str) -> bool: ...


@dataclass
class ServerState:
    """Everything a tool needs, built once at start-up."""

    settings: Settings
    allow: AllowList
    db: Database | None = None
    sheets: Any = None  # SheetsBackend (see sheets.py)
    audit: AuditSink | None = None
    limiter: Limiter | None = None
    auth_enabled: bool = False
    tool_scopes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_settings(cls, settings: Settings, **kwargs: Any) -> ServerState:
        allow = AllowList(
            schemas=tuple(settings.allowed_schemas), tables=tuple(settings.allowed_tables)
        )
        return cls(settings=settings, allow=allow, **kwargs)


@dataclass(frozen=True)
class Caller:
    identity: str
    scopes: frozenset[str] | None  # None = local (stdio): every registered tool is allowed
    client_id: str | None = None


def current_caller() -> Caller:
    token = get_access_token()
    if token is None:
        return Caller(identity=LOCAL_CALLER, scopes=None)
    identity = token.subject or token.client_id or "unknown"
    return Caller(identity=identity, scopes=frozenset(token.scopes), client_id=token.client_id)


def _row_count(result: Any) -> int | None:
    structured = result[1] if isinstance(result, tuple) and len(result) == 2 else result
    if isinstance(structured, dict):
        count = structured.get("row_count")
        return count if isinstance(count, int) else None
    return None


def _classify(exc: BaseException) -> tuple[str, str]:
    """Map a failed call to (audit outcome, safe error text)."""
    cause = exc.__cause__ if isinstance(exc, ToolError) and exc.__cause__ else exc
    if isinstance(cause, SafeToolError):
        return cause.outcome, cause.message
    if isinstance(cause, ValidationError):
        return "invalid", f"{cause.error_count()} argument validation error(s)"
    if isinstance(exc, ToolError) and str(exc).startswith("Unknown tool"):
        return "not_listed", str(exc)
    return "error", type(cause).__name__


def safe_errors(tool_name: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Only SafeToolError text may reach the AI; anything else becomes a generic message."""

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await fn(*args, **kwargs)
            except SafeToolError:
                raise
            except Exception as exc:
                request_id = request_id_var.get() or "-"
                log.error(
                    "tool %s failed: %s (request_id=%s)",
                    tool_name,
                    type(exc).__name__,
                    request_id,
                    exc_info=log.isEnabledFor(logging.DEBUG),
                )
                raise SafeToolError(
                    f"Internal error while running {tool_name} (request_id {request_id})."
                ) from None

        return wrapper

    return decorator


class GuardedFastMCP(FastMCP[Any]):
    """FastMCP with authorization, rate limiting and auditing around every tool call."""

    def __init__(self, state: ServerState, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.state = state

    def add_guarded_tool(
        self,
        fn: Callable[..., Awaitable[Any]],
        *,
        name: str,
        scope: str,
        title: str,
        description: str,
        annotations: ToolAnnotations,
    ) -> None:
        self.state.tool_scopes[name] = scope
        self.add_tool(
            safe_errors(name)(fn),
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            structured_output=True,
        )

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> Sequence[ContentBlock] | dict[str, Any]:
        state = self.state
        request_id = request_id_var.get() or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        caller = current_caller()
        started = time.perf_counter()
        outcome, error, result = "ok", None, None
        try:
            scope = state.tool_scopes.get(name)
            if (
                scope is not None
                and state.auth_enabled
                and (caller.scopes is None or scope not in caller.scopes)
            ):
                raise ForbiddenError(
                    f"Forbidden: {name} requires the '{scope}' scope, "
                    "which your access token does not grant."
                )
            if state.limiter is not None and not state.limiter.allow(caller.identity):
                raise RateLimitedError(
                    f"Rate limit exceeded: at most {state.settings.rate_limit_per_min} tool calls "
                    "per minute. Wait a moment and try again."
                )
            result = await super().call_tool(name, arguments)
            return result
        except BaseException as exc:
            outcome, error = _classify(exc)
            raise
        finally:
            request_id_var.reset(token)
            if state.audit is not None:
                state.audit.record(
                    request_id=request_id,
                    caller=caller.identity,
                    client_id=caller.client_id,
                    tool=name,
                    arguments=dict(arguments or {}),
                    duration_ms=(time.perf_counter() - started) * 1000,
                    row_count=_row_count(result),
                    outcome=outcome,
                    error=error,
                )
