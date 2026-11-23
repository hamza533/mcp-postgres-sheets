from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.observability import _scrub, init_sentry


def test_off_without_dsn() -> None:
    assert init_sentry(Settings()) is False


def test_init_is_privacy_preserving(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    fake = types.ModuleType("sentry_sdk")
    fake.init = lambda **kwargs: calls.append(kwargs)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake)
    assert init_sentry(Settings(sentry_dsn="https://key@o1.ingest.sentry.io/1")) is True
    (kwargs,) = calls
    assert kwargs["send_default_pii"] is False
    assert kwargs["include_local_variables"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["traces_sample_rate"] == 0.0


def test_missing_sdk_is_a_warning_not_a_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    assert init_sentry(Settings(sentry_dsn="https://key@o1.ingest.sentry.io/1")) is False


def test_scrub_removes_messages_and_requests() -> None:
    event = {
        "request": {"data": "SELECT secret"},
        "user": {"id": "x"},
        "exception": {"values": [{"type": "ValueError", "value": "bad value: 'Ava Smith'"}]},
    }
    out = _scrub(event, {})
    assert out is not None
    assert "request" not in out and "user" not in out
    assert out["exception"]["values"][0]["value"] == "ValueError"
