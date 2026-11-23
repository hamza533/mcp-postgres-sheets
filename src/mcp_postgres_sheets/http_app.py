"""Remote mode: Streamable HTTP + OAuth 2.1 bearer tokens.

Routes:
  POST /mcp                                        MCP endpoint (401 without a valid token)
  GET  /.well-known/oauth-protected-resource/mcp   RFC 9728 protected-resource metadata
  GET  /health                                     liveness (process is up)
  GET  /ready                                      readiness (database and Sheets credentials work)

The server runs in stateless mode with JSON responses, so any replica can answer any request.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import uvicorn
from mcp.server.auth.routes import create_protected_resource_routes
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mcp_postgres_sheets import __version__
from mcp_postgres_sheets.auth import SCOPES, JWTTokenVerifier
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.errors import SafeToolError
from mcp_postgres_sheets.ratelimit import RateLimiter
from mcp_postgres_sheets.server import close_state
from mcp_postgres_sheets.tools._runtime import GuardedFastMCP, ServerState, request_id_var

log = logging.getLogger(__name__)

READY_TIMEOUT_S = 5.0
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def http_server_kwargs(settings: Settings) -> dict[str, Any]:
    """FastMCP constructor arguments for remote mode."""
    assert settings.oauth_issuer and settings.oauth_audience  # enforced by Settings
    public = urlparse(settings.public_url or f"http://localhost:{settings.http_port}")
    hosts = ["localhost:*", "127.0.0.1:*", "[::1]:*", f"localhost:{settings.http_port}"]
    if public.netloc:
        hosts += [public.netloc, f"{public.hostname}:*"]
    hosts += settings.http_allowed_hosts
    origins = ["http://localhost:*", "http://127.0.0.1:*"]
    if public.scheme and public.netloc:
        origins.append(f"{public.scheme}://{public.netloc}")
    return {
        "host": settings.http_host,
        "port": settings.http_port,
        "stateless_http": True,
        "json_response": True,
        "streamable_http_path": "/mcp",
        "token_verifier": JWTTokenVerifier(
            issuer=settings.oauth_issuer,
            audience=settings.oauth_audience,
            jwks_url=settings.oauth_jwks_url,
        ),
        "auth": AuthSettings(
            issuer_url=AnyHttpUrl(settings.oauth_issuer),
            resource_server_url=AnyHttpUrl(settings.resource_url),
            required_scopes=None,  # scopes are checked per tool (see tools/_runtime.py)
            validate_token_resource=False,  # the verifier checks `aud` itself
        ),
        "transport_security": TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(dict.fromkeys(hosts)),
            allowed_origins=list(dict.fromkeys(origins)),
        ),
    }


class RequestIdMiddleware:
    """Accept or create X-Request-ID, expose it to the audit log, echo it, add safe headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store"),
                    (b"referrer-policy", b"no-referrer"),
                ]
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            request_id_var.reset(token)


async def readiness(state: ServerState) -> tuple[bool, dict[str, str]]:
    checks: dict[str, str] = {}

    async def run(name: str, probe: Any) -> None:
        try:
            async with asyncio.timeout(READY_TIMEOUT_S):
                await probe()
            checks[name] = "ok"
        except (SafeToolError, TimeoutError):
            checks[name] = "unavailable"
        except Exception:
            checks[name] = "error"

    if state.db is not None:
        await run("database", state.db.ping)
    if state.sheets is not None:
        await run("sheets", state.sheets.check)
    ok = bool(checks) and all(v == "ok" for v in checks.values())
    return ok, checks


def build_http_app(mcp: GuardedFastMCP, state: ServerState) -> Starlette:
    settings = state.settings
    state.auth_enabled = True
    state.limiter = RateLimiter(settings.rate_limit_per_min)

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)  # type: ignore[untyped-decorator]
    async def health(_: Request) -> Response:
        return JSONResponse({"status": "ok", "version": __version__})

    @mcp.custom_route("/ready", methods=["GET"], include_in_schema=False)  # type: ignore[untyped-decorator]
    async def ready(_: Request) -> Response:
        ok, checks = await readiness(state)
        return JSONResponse(
            {"status": "ready" if ok else "not_ready", "checks": checks},
            status_code=200 if ok else 503,
        )

    app = mcp.streamable_http_app()

    # The SDK advertises only `required_scopes` in the metadata; we check scopes per tool, so
    # replace that route with one that lists every scope this server understands.
    assert settings.oauth_issuer
    metadata_routes = create_protected_resource_routes(
        resource_url=AnyHttpUrl(settings.resource_url),
        authorization_servers=[AnyHttpUrl(settings.oauth_issuer)],
        scopes_supported=list(SCOPES),
        resource_name="mcp-postgres-sheets",
        resource_documentation=AnyHttpUrl(
            "https://github.com/hamza533/mcp-postgres-sheets#remote-mode"
        ),
    )
    paths = {r.path for r in metadata_routes}
    app.router.routes[:] = [
        r for r in app.router.routes if not (isinstance(r, Route) and r.path in paths)
    ]
    app.router.routes.extend(metadata_routes)
    app.add_middleware(RequestIdMiddleware)

    # Process-wide resources live in the *app* lifespan (FastMCP's own lifespan runs per
    # request in stateless mode).
    session_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(asgi_app: Starlette) -> AsyncIterator[None]:
        if state.db is not None:
            await state.db.open()
        try:
            async with session_lifespan(asgi_app):
                yield
        finally:
            await close_state(state)

    app.router.lifespan_context = lifespan
    return app


def run_http(mcp: GuardedFastMCP, settings: Settings) -> None:
    app = build_http_app(mcp, mcp.state)
    log.info(
        "remote mode: listening on %s:%s, issuer %s",
        settings.http_host,
        settings.http_port,
        settings.oauth_issuer,
    )
    uvicorn.run(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level="warning",
        access_log=False,  # every tool call is in the audit log; no tokens in access logs
        proxy_headers=True,
        timeout_graceful_shutdown=15,
    )
