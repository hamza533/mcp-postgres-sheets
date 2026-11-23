"""Errors returned to the AI.

Every message here is written for the model: short, actionable, and free of connection
strings, hostnames, stack traces or raw driver output. Each error has an `outcome` used in the
audit log.
"""

from __future__ import annotations

from mcp.server.fastmcp.exceptions import ToolError


class SafeToolError(ToolError):
    """A tool failure whose message is safe to show to the AI and to log."""

    outcome = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BlockedError(SafeToolError):
    """The request was rejected by a safety layer (SQL check, allow-list, read-only mode)."""

    outcome = "blocked"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Rejected: {reason}")
        self.reason = reason


class InvalidInputError(SafeToolError):
    outcome = "invalid"


class NotFoundError(SafeToolError):
    outcome = "not_found"


class TimeoutError_(SafeToolError):  # trailing underscore: not the builtin TimeoutError
    outcome = "timeout"


class ForbiddenError(SafeToolError):
    """The caller's token lacks the scope this tool needs (remote mode)."""

    outcome = "forbidden"


class RateLimitedError(SafeToolError):
    outcome = "rate_limited"


class UnavailableError(SafeToolError):
    """A backend (database, Google API) is not configured or not reachable."""

    outcome = "unavailable"
