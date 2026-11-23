from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_postgres_sheets.config import Settings, Transport


def test_defaults_are_safe() -> None:
    s = Settings()
    assert s.read_only is True
    assert s.allowed_schemas == ["public"]
    assert s.allowed_tables == []
    assert s.allowed_sheet_ids == []
    assert s.max_rows == 500
    assert s.query_timeout_ms == 5000
    assert s.redact_args is True
    assert s.transport is Transport.STDIO
    assert s.rate_limit_per_min == 60


def test_comma_lists_are_split_and_normalised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_SCHEMAS", "public, Sales ,")
    monkeypatch.setenv("ALLOWED_TABLES", "orders,Public.Customers")
    monkeypatch.setenv("ALLOWED_SHEET_IDS", "abc123,def456")
    s = Settings()
    assert s.allowed_schemas == ["public", "sales"]
    assert s.allowed_tables == ["orders", "public.customers"]
    assert s.allowed_sheet_ids == ["abc123", "def456"]


def test_secrets_never_render(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:supersecret@h/db")
    s = Settings()
    assert "supersecret" not in repr(s)
    assert "supersecret" not in str(s.model_dump())


def test_http_requires_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSPORT", "http")
    with pytest.raises(ValidationError, match="OAUTH_ISSUER"):
        Settings()
    monkeypatch.setenv("OAUTH_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("OAUTH_AUDIENCE", "mcp")
    assert Settings().transport is Transport.HTTP


def test_empty_values_mean_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("AUDIT_LOG_PATH", "")
    monkeypatch.setenv("ALLOWED_TABLES", "")
    s = Settings()
    assert s.database_url is None
    assert s.audit_log_path is None
    assert s.allowed_tables == []


def test_limits_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_ROWS", "0")
    with pytest.raises(ValidationError):
        Settings()
