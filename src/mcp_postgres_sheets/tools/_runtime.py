"""The wrapper every tool goes through: scope check → rate limit → run → audit.

It also guarantees that only `SafeToolError` messages ever reach the AI: any other exception is
replaced with a generic message (the details go to the server log, never to the client).
"""

from __future__ import annotations

import functools
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ParamSpec, Protocol, TypeVar

from mcp.server.auth.middleware.auth_context import get_access_token

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.errors import ForbiddenError, RateLimitedError, SafeToolError
from mcp_postgres_sheets.sql_guard import AllowList

if TYPE_CHECKING:
    from mcp_postgres_sheets.db import Database

log = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

LOCAL_CALLER = "local"


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


class SheetsLike(Protocol):
    async def aclose(self) -> None: ...


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
    extra: dict[str, Any] = field(default_factory=dict)

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


def result_row_count(result: Any) -> int | None:
    count = getattr(result, "row_count", None)
    return count if isinstance(count, int) else None


def instrument(
    state: ServerState, tool_name: str, scope: str
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorate a tool coroutine with authorization, rate limiting, error hygiene and audit."""

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request_id = uuid.uuid4().hex
            caller = current_caller()
            started = time.perf_counter()
            outcome = "ok"
            error_message: str | None = None
            result: R | None = None
            try:
                if state.auth_enabled and (caller.scopes is None or scope not in caller.scopes):
                    raise ForbiddenError(
                        f"Forbidden: this tool requires the '{scope}' scope, "
                        "which your access token does not grant."
                    )
                if state.limiter is not None and not state.limiter.allow(caller.identity):
                    raise RateLimitedError(
                        f"Rate limit exceeded: at most {state.settings.rate_limit_per_min} "
                        "tool calls per minute. Wait a moment and try again."
                    )
                result = await fn(*args, **kwargs)
                return result
            except SafeToolError as exc:
                outcome = exc.outcome
                error_message = exc.message
                raise
            except Exception as exc:
                outcome = "error"
                error_message = "internal error"
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
            finally:
                if state.audit is not None:
                    state.audit.record(
                        request_id=request_id,
                        caller=caller.identity,
                        client_id=caller.client_id,
                        tool=tool_name,
                        arguments=dict(kwargs),
                        duration_ms=(time.perf_counter() - started) * 1000,
                        row_count=result_row_count(result),
                        outcome=outcome,
                        error=error_message,
                    )

        return wrapper

    return decorator
