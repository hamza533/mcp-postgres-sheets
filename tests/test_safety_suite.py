"""The safety suite (SPEC §7.1) must pass at 100% in CI."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest

from eval.safety import STOPPED, SafetyCase, SafetyRunner, load_cases

CASES = load_cases()

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def runner() -> AsyncIterator[SafetyRunner]:
    r = SafetyRunner(
        {
            "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", ""),
            "QUERY_TIMEOUT_MS": "1500",
            "SHEETS_BACKEND": "memory",
        }
    )
    yield r
    await r.aclose()


def test_suite_has_at_least_40_cases() -> None:
    assert len(CASES) >= 40
    assert all(c.expect in STOPPED for c in CASES)


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
async def test_case_is_stopped(case: SafetyCase, runner: SafetyRunner) -> None:
    result = await runner.run(case)
    assert result.passed, f"{case.id}: expected {case.expect}, got {result.actual}: {result.detail}"
