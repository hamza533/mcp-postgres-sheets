"""A minimal tool-calling loop: the LLM plays the AI assistant, the MCP server is the real one."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp.client.session import ClientSession
from mcp.types import TextContent, Tool

from eval.llm import LLM

MAX_STEPS = 10


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    is_error: bool


@dataclass
class AgentResult:
    answer: str
    calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    error: str | None = None


def declarations(tools: list[Tool]) -> list[dict[str, Any]]:
    """MCP tool definitions → Gemini function declarations (JSON Schema passed through)."""
    return [
        {"name": t.name, "description": t.description or "", "parametersJsonSchema": t.inputSchema}
        for t in tools
    ]


def system_prompt(instructions: str, today: str) -> str:
    return (
        f"You are a data assistant for a small online shop. Today is {today}. {instructions} "
        "Always use the tools to look things up; never guess numbers or names. When you are done, "
        "reply with a short final answer that states the specific values asked for."
    )


async def run_agent(
    llm: LLM, session: ClientSession, tools: list[Tool], system: str, prompt: str
) -> AgentResult:
    decls = declarations(tools)
    contents: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": prompt}]}]
    result = AgentResult(answer="")
    for step in range(1, MAX_STEPS + 1):
        result.steps = step
        turn = await llm.generate(system, contents, decls)
        contents.append({"role": "model", "parts": turn.parts})
        calls = turn.function_calls
        if not calls:
            result.answer = turn.text.strip()
            return result
        responses = []
        for call in calls:
            name, args = call.get("name", ""), call.get("args") or {}
            res = await session.call_tool(name, args)
            result.calls.append(ToolCall(name, args, bool(res.isError)))
            if res.isError or res.structuredContent is None:
                text = " ".join(c.text for c in res.content if isinstance(c, TextContent))
                payload: dict[str, Any] = {"error" if res.isError else "result": text}
            else:
                payload = res.structuredContent
            response: dict[str, Any] = {"name": name, "response": payload}
            if "id" in call:
                response["id"] = call["id"]
            responses.append({"functionResponse": response})
        contents.append({"role": "user", "parts": responses})
    result.error = f"no final answer after {MAX_STEPS} steps"
    return result
