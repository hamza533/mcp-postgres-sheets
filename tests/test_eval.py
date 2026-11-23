"""The evaluation harness itself: agent loop (scripted fake LLM), task checks, report rendering."""

from __future__ import annotations

import os
from typing import Any

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from eval.agent import declarations, run_agent
from eval.llm import GeminiClient, ModelTurn
from eval.run import render_md
from eval.tasks import TASKS, TaskContext, numbers_in, refusal
from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.server import build_server, close_state
from mcp_postgres_sheets.sheets import MemorySheetsBackend


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class ScriptedLLM:
    model = "scripted"

    def __init__(self, turns: list[list[dict[str, Any]]]) -> None:
        self.turns = turns
        self.seen: list[list[dict[str, Any]]] = []

    async def generate(
        self, system: str, contents: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn:
        self.seen.append(list(contents))
        return ModelTurn(parts=self.turns.pop(0))


def test_numbers_in() -> None:
    assert numbers_in("Total: $12,345.67 from 3 orders (4.5%)") == [12345.67, 3.0, 4.5]


@pytest.mark.anyio
async def test_refusal_check() -> None:
    check = refusal()
    ok, _ = await check(None, "I can't do that: the database connection is read-only.")  # type: ignore[arg-type]
    assert ok
    bad, _ = await check(None, "Done! I deleted 167 cancelled orders.")  # type: ignore[arg-type]
    assert not bad


def test_gemini_parse_skips_thoughts() -> None:
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "thinking…", "thought": True},
                        {"text": "Answer"},
                        {"functionCall": {"name": "x", "args": {}}},
                    ]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "thoughtsTokenCount": 2,
        },
    }
    turn = GeminiClient._parse(data)
    assert turn.text == "Answer" and turn.function_calls == [{"name": "x", "args": {}}]
    assert (turn.prompt_tokens, turn.output_tokens) == (10, 7)


def test_report_renders_without_tasks() -> None:
    md = render_md({"tasks": {"skipped": "GEMINI_API_KEY is not set"}})
    assert "Not run: GEMINI_API_KEY is not set" in md


@pytest.mark.integration
@pytest.mark.anyio
async def test_agent_loop_runs_real_tools() -> None:
    settings = Settings.model_validate({"database_url": os.environ.get("TEST_DATABASE_URL", "")})
    mcp, state = build_server(settings)
    llm = ScriptedLLM(
        [
            [
                {
                    "functionCall": {
                        "name": "postgres_query",
                        "args": {"sql": "SELECT count(*) AS n FROM customers"},
                    }
                }
            ],
            [{"functionCall": {"name": "postgres_query", "args": {"sql": "DROP TABLE customers"}}}],
            [{"text": "We have 500 customers."}],
        ]
    )
    try:
        async with create_connected_server_and_client_session(mcp._mcp_server) as client:
            tools = (await client.list_tools()).tools
            assert {d["name"] for d in declarations(tools)} == {t.name for t in tools}
            result = await run_agent(llm, client, tools, "system", "How many customers?")
    finally:
        await close_state(state)
    assert result.answer == "We have 500 customers."
    assert [c.name for c in result.calls] == ["postgres_query", "postgres_query"]
    assert [c.is_error for c in result.calls] == [False, True]
    first_response = llm.seen[1][-1]["parts"][0]["functionResponse"]
    assert first_response["response"]["rows"] == [{"n": 500}]
    error_response = llm.seen[2][-1]["parts"][0]["functionResponse"]["response"]
    assert "Rejected" in error_response["error"]


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.parametrize("task", TASKS, ids=[t.id for t in TASKS])
async def test_no_task_passes_on_an_empty_answer(task: Any) -> None:
    settings = Settings.model_validate({"database_url": os.environ.get("TEST_DATABASE_URL", "")})
    _, state = build_server(settings)
    try:
        assert state.db is not None
        ctx = TaskContext(db=state.db, sheets=MemorySheetsBackend.from_file(None))
        results = [await check(ctx, "") for check in task.checks]
    finally:
        await close_state(state)
    assert not all(ok for ok, _ in results), task.id
