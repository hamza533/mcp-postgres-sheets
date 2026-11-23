"""End-to-end checks for remote mode against `docker compose --profile remote up`.

    make remote-smoke            # from the host
    MCP_URL=http://mcp:8765 TOKEN_URL=http://keycloak:8080/realms/mcp/protocol/openid-connect/token \
        uv run python -m scripts.remote_smoke   # from inside the compose network

Uses the Keycloak test clients from deploy/keycloak/mcp-realm.json (client-credentials grant).
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import Any

import httpx

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8765").rstrip("/")
TOKEN_URL = os.environ.get(
    "TOKEN_URL", "http://localhost:8180/realms/mcp/protocol/openid-connect/token"
)
CLIENTS = {
    "reader": ("mcp-reader", "reader-dev-secret"),
    "writer": ("mcp-writer", "writer-dev-secret"),
    "db_only": ("mcp-db-only", "db-only-dev-secret"),
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def get_token(client: httpx.Client, who: str) -> str:
    client_id, secret = CLIENTS[who]
    resp = client.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": secret},
    )
    resp.raise_for_status()
    return str(resp.json()["access_token"])


def rpc(
    client: httpx.Client, method: str, params: dict[str, Any] | None, token: str | None
) -> httpx.Response:
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post(f"{MCP_URL}/mcp", json=body, headers=headers)


def call(client: httpx.Client, tool: str, args: dict[str, Any], token: str) -> dict[str, Any]:
    resp = rpc(client, "tools/call", {"name": tool, "arguments": args}, token)
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()["result"]
    return result


def main() -> int:
    with httpx.Client(timeout=15) as client:
        r = client.get(f"{MCP_URL}/health")
        check("GET /health → 200", r.status_code == 200, r.text)
        r = client.get(f"{MCP_URL}/ready")
        check("GET /ready → 200 (database + sheets reachable)", r.status_code == 200, r.text)

        r = rpc(client, "tools/list", None, None)
        challenge = r.headers.get("www-authenticate", "")
        check("no token → 401", r.status_code == 401, str(r.status_code))
        check("401 carries resource_metadata pointer", "resource_metadata=" in challenge, challenge)

        r = client.get(f"{MCP_URL}/.well-known/oauth-protected-resource/mcp")
        meta = r.json() if r.status_code == 200 else {}
        check(
            "protected-resource metadata lists the issuer and 3 scopes",
            bool(meta.get("authorization_servers")) and len(meta.get("scopes_supported", [])) == 3,
            r.text,
        )

        r = rpc(client, "tools/list", None, "eyJhbGciOiJSUzI1NiJ9.e30.invalid")
        check("forged token → 401", r.status_code == 401, str(r.status_code))

        reader, writer, db_only = (get_token(client, w) for w in ("reader", "writer", "db_only"))

        r = rpc(client, "tools/list", None, reader)
        tools = (
            [t["name"] for t in r.json().get("result", {}).get("tools", [])]
            if r.status_code == 200
            else []
        )
        check("reader token: tools/list → 8 tools", len(tools) == 8, str(tools))

        res = call(client, "postgres_query", {"sql": "SELECT count(*) AS n FROM customers"}, reader)
        check(
            "reader token: postgres_query works",
            not res["isError"] and res["structuredContent"]["rows"] == [{"n": 500}],
            str(res),
        )

        res = call(client, "postgres_query", {"sql": "DROP TABLE customers"}, reader)
        check(
            "reader token: DROP TABLE is rejected",
            res["isError"] and "Rejected" in res["content"][0]["text"],
            str(res),
        )

        res = call(
            client,
            "sheets_read_range",
            {"sheet_id": "demo-sales-pipeline", "range": "Leads!A1:C2"},
            db_only,
        )
        check(
            "db:read-only token: sheets_read_range → forbidden",
            res["isError"] and "sheets:read" in res["content"][0]["text"],
            str(res),
        )

        row = {
            "sheet_id": "demo-sales-pipeline",
            "tab": "Notes",
            "rows": [["2026-11-23", "remote smoke test"]],
        }
        res = call(
            client,
            "sheets_append_rows",
            {**row, "idempotency_key": f"smoke-{uuid.uuid4()}"},
            reader,
        )
        check(
            "token without sheets:write cannot append",
            res["isError"] and "sheets:write" in res["content"][0]["text"],
            str(res),
        )

        key = f"smoke-{uuid.uuid4()}"
        first = call(client, "sheets_append_rows", {**row, "idempotency_key": key}, writer)
        again = call(client, "sheets_append_rows", {**row, "idempotency_key": key}, writer)
        check(
            "writer token: append works",
            not first["isError"] and first["structuredContent"]["updated_rows"] == 1,
            str(first),
        )
        check(
            "same idempotency_key → not written twice",
            not again["isError"] and again["structuredContent"]["duplicate"] is True,
            str(again),
        )

    print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
