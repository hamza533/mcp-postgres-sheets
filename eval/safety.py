"""Safety suite runner, shared by `tests/test_safety_suite.py` (CI) and `make eval`.

Each case in `safety_cases.json` is sent through a real MCP client session (in memory) to a
server built from the case's configuration, against the real sample Postgres. The outcome is
read from the tool result the AI would see.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult, TextContent

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.server import build_server
from mcp_postgres_sheets.tools._runtime import ServerState

CASES_PATH = Path(__file__).with_name("safety_cases.json")

# Outcomes that count as "the attempt was stopped".
STOPPED = {"blocked", "invalid", "timeout", "capped", "not_listed", "forbidden"}


@dataclass(frozen=True)
class SafetyCase:
    id: str
    category: str
    title: str
    tool: str
    args: dict[str, Any]
    expect: str
    config: dict[str, str] = field(default_factory=dict)
    scopes: tuple[str, ...] | None = None


@dataclass(frozen=True)
class CaseResult:
    case: SafetyCase
    actual: str
    detail: str
    duration_ms: float

    @property
    def passed(self) -> bool:
        return self.actual == self.case.expect


def _expand(value: Any) -> Any:
    # "@@REPEAT:<text>:<n>" builds oversized inputs without bloating the JSON file.
    if isinstance(value, str) and value.startswith("@@REPEAT:"):
        text, times = value.removeprefix("@@REPEAT:").rsplit(":", 1)
        return text * int(times)
    return value


def load_cases(path: Path = CASES_PATH) -> list[SafetyCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for item in raw["cases"]:
        cases.append(
            SafetyCase(
                id=item["id"],
                category=item["category"],
                title=item["title"],
                tool=item["tool"],
                args={k: _expand(v) for k, v in item["args"].items()},
                expect=item["expect"],
                config=dict(item.get("config", {})),
                scopes=tuple(item["scopes"]) if "scopes" in item else None,
            )
        )
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate safety case ids")
    return cases


def classify(result: CallToolResult) -> tuple[str, str]:
    text = " ".join(c.text for c in result.content if isinstance(c, TextContent))
    if not result.isError:
        data = result.structuredContent or {}
        if data.get("truncated") is True:
            return "capped", f"{data.get('row_count')} rows returned, truncated"
        return "allowed", text[:200]
    if "Rejected:" in text:
        return "blocked", text
    if "Query cancelled" in text:
        return "timeout", text
    if "Forbidden:" in text:
        return "forbidden", text
    if "validation error" in text:
        return "invalid", text.splitlines()[0]
    if "Unknown tool" in text:
        return "not_listed", text
    return "error", text


def settings_for(base: Mapping[str, str], overrides: Mapping[str, str]) -> Settings:
    merged = {k.lower(): v for k, v in {**base, **overrides}.items()}
    return Settings.model_validate(merged)


class SafetyRunner:
    """Runs cases, reusing one server per distinct configuration."""

    def __init__(self, base_env: Mapping[str, str]) -> None:
        self.base_env = dict(base_env)
        self._states: list[ServerState] = []

    @asynccontextmanager
    async def _session(self, case: SafetyCase) -> AsyncIterator[Any]:
        settings = settings_for(self.base_env, case.config)
        mcp, state = build_server(settings)
        self._states.append(state)
        if case.scopes is not None:
            state.auth_enabled = True
            token = AccessToken(
                token="safety-suite", client_id="safety-suite", scopes=list(case.scopes)
            )
            reset = auth_context_var.set(AuthenticatedUser(token))
        else:
            reset = None
        try:
            async with create_connected_server_and_client_session(mcp._mcp_server) as client:
                yield client
        finally:
            if reset is not None:
                auth_context_var.reset(reset)

    async def run(self, case: SafetyCase) -> CaseResult:
        started = time.perf_counter()
        async with self._session(case) as client:
            listed = {t.name for t in (await client.list_tools()).tools}
            if case.tool not in listed:
                result = await client.call_tool(case.tool, case.args)
                actual = "not_listed" if result.isError else "allowed"
                detail = "tool is not registered"
            else:
                result = await client.call_tool(case.tool, case.args)
                actual, detail = classify(result)
        return CaseResult(case, actual, detail, (time.perf_counter() - started) * 1000)

    async def aclose(self) -> None:
        async with AsyncExitStack():
            for state in self._states:
                if state.db is not None:
                    await state.db.close()
                if state.sheets is not None:
                    await state.sheets.aclose()
        self._states.clear()
