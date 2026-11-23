"""Shared fixtures.

Integration tests need a real Postgres seeded with sample_data (``make db``) and
``TEST_DATABASE_URL`` pointing at the read-only role. Without it they are skipped — unless
``REQUIRE_INTEGRATION=1`` (set by ``make test`` and CI), in which case they fail loudly so a
missing database can never turn the safety suite into a silent pass.
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("TEST_DATABASE_URL"):
        return
    if os.environ.get("REQUIRE_INTEGRATION") == "1":
        raise pytest.UsageError("REQUIRE_INTEGRATION=1 but TEST_DATABASE_URL is not set")
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set (run `make db`)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never read the developer's .env file or ambient server settings."""
    for key in list(os.environ):
        if key in {"TEST_DATABASE_URL", "REQUIRE_INTEGRATION"}:
            continue
        if key.startswith(
            ("DATABASE_", "ALLOWED_", "OAUTH_", "SHEETS_", "GOOGLE_", "HTTP_")
        ) or key in {
            "READ_ONLY",
            "TRANSPORT",
            "MAX_ROWS",
            "QUERY_TIMEOUT_MS",
            "AUDIT_LOG_PATH",
            "REDACT_ARGS",
            "RATE_LIMIT_PER_MIN",
            "PUBLIC_URL",
            "SENTRY_DSN",
        }:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(os.path.dirname(__file__))  # no .env in tests/
