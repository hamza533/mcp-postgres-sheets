"""Optional error tracking with Sentry (SENTRY_DSN). Off unless the DSN is set.

Install with the extra: `uvx --from 'mcp-postgres-sheets[sentry]' mcp-postgres-sheets`.
Only exceptions and their stack frames' code locations are sent: no request bodies, no local
variables, no PII, no performance traces.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_postgres_sheets import __version__
from mcp_postgres_sheets.config import Settings

log = logging.getLogger(__name__)


def _scrub(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    # Belt and braces: drop anything that could carry query text or row values.
    event.pop("request", None)
    event.pop("user", None)
    for exc in (event.get("exception") or {}).get("values", []):
        exc["value"] = exc.get("type", "error")  # the message may contain SQL or cell values
    return event


def init_sentry(settings: Settings) -> bool:
    if settings.sentry_dsn is None:
        return False
    try:
        import sentry_sdk
    except ImportError:
        log.warning("SENTRY_DSN is set but sentry-sdk is not installed (use the [sentry] extra)")
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        release=f"mcp-postgres-sheets@{__version__}",
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        before_send=_scrub,
    )
    log.info("Sentry error tracking enabled")
    return True
