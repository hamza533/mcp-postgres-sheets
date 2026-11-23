"""The one place the evaluation talks to an LLM (Gemini API, REST via httpx).

The MCP server itself never calls an LLM. This client is only used by `make eval` to play the
role of an AI assistant. Swapping providers means changing this module only.

* Free-tier friendly: requests are throttled (GEMINI_RPM, default 8/min) and retried on 429.
* Cached: identical requests are answered from eval/.cache/gemini/ (re-runs cost nothing and are
  reproducible).
* Token usage of every request is recorded.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
CACHE_DIR = Path(__file__).parent / ".cache" / "gemini"


@dataclass
class ModelTurn:
    parts: list[dict[str, Any]]  # the model's content parts, echoed back verbatim in history
    prompt_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False

    @property
    def function_calls(self) -> list[dict[str, Any]]:
        return [p["functionCall"] for p in self.parts if "functionCall" in p]

    @property
    def text(self) -> str:
        return "".join(p.get("text", "") for p in self.parts if not p.get("thought"))


class LLM(Protocol):
    model: str

    async def generate(
        self, system: str, contents: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn: ...


@dataclass
class Usage:
    requests: int = 0
    cached_requests: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    per_request: list[dict[str, int]] = field(default_factory=list)

    def add(self, turn: ModelTurn) -> None:
        self.requests += 1
        self.cached_requests += int(turn.cached)
        self.prompt_tokens += turn.prompt_tokens
        self.output_tokens += turn.output_tokens
        self.per_request.append({"prompt": turn.prompt_tokens, "output": turn.output_tokens})


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        rpm: int = 8,
        cache_dir: Path = CACHE_DIR,
        timeout_s: float = 60.0,
    ) -> None:
        self.model = model
        self._key = api_key
        self._interval = 60.0 / max(rpm, 1)
        self._last = 0.0
        self._cache_dir = cache_dir
        self._timeout = timeout_s
        self.usage = Usage()

    @classmethod
    def from_env(cls) -> GeminiClient | None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            return None
        return cls(
            api_key=key,
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip(),
            rpm=int(os.environ.get("GEMINI_RPM", "8")),
        )

    def _body(
        self, system: str, contents: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "tools": [{"functionDeclarations": tools}],
            "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
            "generationConfig": {"temperature": 0},
        }

    async def generate(
        self, system: str, contents: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> ModelTurn:
        body = self._body(system, contents, tools)
        digest = hashlib.sha256(
            json.dumps({"m": self.model, "b": body}, sort_keys=True).encode()
        ).hexdigest()
        cache_file = self._cache_dir / f"{digest}.json"
        if cache_file.is_file():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            turn = self._parse(data)
            turn.cached = True
            self.usage.add(turn)
            return turn

        data = await self._post(body)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        turn = self._parse(data)
        self.usage.add(turn)
        return turn

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{API_BASE}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(6):
                wait = self._last + self._interval - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._last = time.monotonic()
                resp = await client.post(url, json=body, headers={"x-goog-api-key": self._key})
                if resp.status_code in (429, 500, 503) and attempt < 5:
                    await asyncio.sleep(self._retry_delay(resp, attempt))
                    continue
                if resp.status_code >= 400:
                    # Never echo the request (it carries the key in a header only, but be strict).
                    raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:300]}")
                result: dict[str, Any] = resp.json()
                return result
        raise RuntimeError("Gemini API: too many retries")

    @staticmethod
    def _retry_delay(resp: httpx.Response, attempt: int) -> float:
        try:
            for detail in resp.json().get("error", {}).get("details", []):
                delay = detail.get("retryDelay")
                if isinstance(delay, str) and delay.endswith("s"):
                    return min(float(delay[:-1]) + 1, 90.0)
        except (ValueError, AttributeError):
            pass
        return float(min(60.0, 4.0 * 2**attempt) * random.uniform(0.75, 1.25))

    @staticmethod
    def _parse(data: dict[str, Any]) -> ModelTurn:
        candidates = data.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []
        usage = data.get("usageMetadata", {})
        return ModelTurn(
            parts=parts,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            output_tokens=int(usage.get("candidatesTokenCount", 0))
            + int(usage.get("thoughtsTokenCount", 0)),
        )
