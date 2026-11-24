"""Remote mode: Streamable HTTP + OAuth bearer tokens, exercised in-process over ASGI."""

from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from mcp_postgres_sheets.audit import MemoryAudit
from mcp_postgres_sheets.auth import JWTTokenVerifier, extract_scopes
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.http_app import build_http_app
from mcp_postgres_sheets.ratelimit import RateLimiter
from mcp_postgres_sheets.server import build_server

ISS = "https://idp.example.com/realms/mcp"
AUD = "mcp-postgres-sheets"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def token(scopes: str = "db:read", **overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISS, "aud": AUD, "sub": "alice", "azp": "test-client",
        "iat": now, "exp": now + 300, "scope": scopes,
    }  # fmt: skip
    claims.update(overrides)
    key = claims.pop("_key", KEY)
    kid = claims.pop("_kid", "k1")
    return jwt.encode(
        {k: v for k, v in claims.items() if v is not None},
        key,
        algorithm="RS256",
        headers={"kid": kid},
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- unit -----------------------------------------------------------------------------------


def test_scope_extraction() -> None:
    assert extract_scopes({"scope": "openid db:read sheets:read"}) == [
        "openid",
        "db:read",
        "sheets:read",
    ]
    assert extract_scopes({"scp": "db.read sheets.write"}) == ["db:read", "sheets:write"]
    assert extract_scopes({"roles": ["sheets.read"], "scope": "sheets:read"}) == ["sheets:read"]
    assert extract_scopes({}) == []


def test_rate_limiter_sliding_window() -> None:
    now = [0.0]
    limiter = RateLimiter(3, clock=lambda: now[0])
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("b") is True  # per caller
    now[0] = 59.9
    assert limiter.allow("a") is False
    now[0] = 60.1
    assert limiter.allow("a") is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    "bad",
    [
        token(exp=int(time.time()) - 120),
        token(aud="someone-else"),
        token(iss="https://evil.example.com"),
        token(_key=OTHER_KEY),
        token(exp=None),
        jwt.encode(
            {"iss": ISS, "aud": AUD, "exp": int(time.time()) + 60}, "s" * 32, algorithm="HS256"
        ),
        "not-a-jwt",
    ],
    ids=["expired", "wrong-aud", "wrong-iss", "wrong-key", "no-exp", "hs256-confusion", "garbage"],
)
async def test_verifier_rejects(bad: str) -> None:
    verifier = JWTTokenVerifier(issuer=ISS, audience=AUD, key_resolver=lambda _: KEY.public_key())
    assert await verifier.verify_token(bad) is None


class FakeJwks:
    """Stands in for PyJWKClient; records whether each call forced a refetch."""

    def __init__(self) -> None:
        jwk = jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
        self.keys = [jwt.PyJWK({**jwk, "kid": "k1", "use": "sig"})]
        self.refreshes: list[bool] = []

    def get_signing_keys(self, refresh: bool = False) -> list[jwt.PyJWK]:
        self.refreshes.append(refresh)
        return self.keys


@pytest.mark.anyio
async def test_unknown_kids_refetch_the_jwks_at_most_once_per_interval() -> None:
    verifier = JWTTokenVerifier(issuer=ISS, audience=AUD, jwks_url="http://idp.invalid/jwks")
    fake = FakeJwks()
    verifier._jwks_client = fake  # type: ignore[assignment]
    assert await verifier.verify_token(token()) is not None
    for i in range(20):  # forged tokens with random kids
        assert await verifier.verify_token(token(_kid=f"forged-{i}", _key=OTHER_KEY)) is None
    assert fake.refreshes.count(True) == 1  # one forced refetch, not twenty


@pytest.mark.anyio
async def test_verifier_accepts() -> None:
    verifier = JWTTokenVerifier(issuer=ISS, audience=AUD, key_resolver=lambda _: KEY.public_key())
    access = await verifier.verify_token(token("db:read sheets:read", aud=[AUD, "account"]))
    assert access is not None
    assert access.subject == "alice" and access.client_id == "test-client"
    assert access.scopes == ["db:read", "sheets:read"] and access.resource == AUD


# --- HTTP ---------------------------------------------------------------------------------------


class Remote:
    def __init__(self, client: httpx.AsyncClient, audit: MemoryAudit) -> None:
        self.client = client
        self.audit = audit

    async def rpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        bearer: str | None = None,
        **headers: str,
    ) -> httpx.Response:
        h = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            **headers,
        }
        if bearer:
            h["Authorization"] = f"Bearer {bearer}"
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        return await self.client.post("/mcp", json=body, headers=h)

    async def call(self, tool: str, args: dict[str, Any], bearer: str) -> dict[str, Any]:
        resp = await self.rpc("tools/call", {"name": tool, "arguments": args}, bearer)
        assert resp.status_code == 200, resp.text
        result: dict[str, Any] = resp.json()["result"]
        return result


@pytest.fixture
async def remote() -> AsyncIterator[Remote]:
    settings = Settings.model_validate(
        {
            "transport": "http",
            "oauth_issuer": ISS,
            "oauth_audience": AUD,
            "public_url": "http://localhost:8765",
            "database_url": os.environ.get("TEST_DATABASE_URL", ""),
            "sheets_backend": "memory",
            "allowed_sheet_ids": "demo-sales-pipeline",
            "read_only": False,
            "rate_limit_per_min": 8,
        }
    )
    mcp, state = build_server(settings)
    mcp._token_verifier = JWTTokenVerifier(
        issuer=ISS, audience=AUD, key_resolver=lambda _: KEY.public_key()
    )
    audit = MemoryAudit()
    state.audit = audit
    app = build_http_app(mcp, state)
    transport = httpx.ASGITransport(app=app)
    async with (
        mcp.session_manager.run(),
        httpx.AsyncClient(transport=transport, base_url="http://localhost:8765") as client,
    ):
        yield Remote(client, audit)
    if state.db is not None:
        await state.db.close()


pytestmark_http = [pytest.mark.integration, pytest.mark.anyio]


@pytest.mark.integration
@pytest.mark.anyio
async def test_no_token_is_401_with_metadata_pointer(remote: Remote) -> None:
    resp = await remote.rpc("tools/list")
    assert resp.status_code == 401
    challenge = resp.headers["www-authenticate"]
    assert challenge.startswith("Bearer")
    assert (
        'resource_metadata="http://localhost:8765/.well-known/oauth-protected-resource/mcp"'
        in challenge
    )
    assert remote.audit.entries == []  # nothing reached a tool


@pytest.mark.integration
@pytest.mark.anyio
async def test_invalid_token_is_401(remote: Remote) -> None:
    for bad in ("garbage", token(_key=OTHER_KEY), token(aud="other")):
        resp = await remote.rpc("tools/list", bearer=bad)
        assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.anyio
async def test_protected_resource_metadata(remote: Remote) -> None:
    resp = await remote.client.get("/.well-known/oauth-protected-resource/mcp")
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["resource"] == "http://localhost:8765/mcp"
    assert meta["authorization_servers"] == [ISS]
    assert meta["scopes_supported"] == ["db:read", "sheets:read", "sheets:write"]


@pytest.mark.integration
@pytest.mark.anyio
async def test_health_and_ready_need_no_token(remote: Remote) -> None:
    health = await remote.client.get("/health")
    assert health.status_code == 200 and health.json()["status"] == "ok"
    ready = await remote.client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "checks": {"database": "ok", "sheets": "ok"}}


@pytest.mark.integration
@pytest.mark.anyio
async def test_valid_token_can_query_and_is_audited_as_subject(remote: Remote) -> None:
    listed = await remote.rpc("tools/list", bearer=token("db:read"))
    assert listed.status_code == 200
    assert len(listed.json()["result"]["tools"]) == 8
    result = await remote.call(
        "postgres_query", {"sql": "SELECT count(*) AS n FROM orders"}, token("db:read")
    )
    assert result["isError"] is False
    assert result["structuredContent"]["rows"] == [{"n": 1500}]
    entry = remote.audit.entries[-1]
    assert (
        entry["caller"] == "alice"
        and entry["client_id"] == "test-client"
        and entry["outcome"] == "ok"
    )


@pytest.mark.integration
@pytest.mark.anyio
async def test_token_without_sheets_write_cannot_append(remote: Remote) -> None:
    args = {
        "sheet_id": "demo-sales-pipeline",
        "tab": "Notes",
        "rows": [["2026-11-23", "hi"]],
        "idempotency_key": "remote-0001",
    }
    denied = await remote.call("sheets_append_rows", args, token("db:read sheets:read"))
    assert denied["isError"] is True
    assert "requires the 'sheets:write' scope" in denied["content"][0]["text"]
    assert remote.audit.entries[-1]["outcome"] == "forbidden"
    allowed = await remote.call("sheets_append_rows", args, token("sheets:write"))
    assert allowed["isError"] is False and allowed["structuredContent"]["updated_rows"] == 1


@pytest.mark.integration
@pytest.mark.anyio
async def test_entra_style_scopes(remote: Remote) -> None:
    result = await remote.call("postgres_list_tables", {}, token(scope=None, scp="db.read"))
    assert result["isError"] is False


@pytest.mark.integration
@pytest.mark.anyio
async def test_rate_limit_per_caller(remote: Remote) -> None:
    bob = token("db:read", sub="bob")
    outcomes = []
    for _ in range(9):
        result = await remote.call("postgres_list_tables", {}, bob)
        outcomes.append(result["isError"])
    assert outcomes == [False] * 8 + [True]
    assert remote.audit.entries[-1]["outcome"] == "rate_limited"
    other = await remote.call("postgres_list_tables", {}, token("db:read", sub="carol"))
    assert other["isError"] is False


@pytest.mark.integration
@pytest.mark.anyio
async def test_request_id_round_trip(remote: Remote) -> None:
    resp = await remote.rpc(
        "tools/call",
        {"name": "postgres_list_tables", "arguments": {}},
        token("db:read"),
        **{"X-Request-ID": "trace-12345678"},
    )
    assert resp.headers["x-request-id"] == "trace-12345678"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert remote.audit.entries[-1]["request_id"] == "trace-12345678"
    assert json.loads(resp.text)["result"]["isError"] is False


@pytest.mark.integration
@pytest.mark.anyio
async def test_dns_rebinding_protection(remote: Remote) -> None:
    resp = await remote.rpc("tools/list", bearer=token(), Host="evil.example.com")
    assert resp.status_code in (400, 421)
