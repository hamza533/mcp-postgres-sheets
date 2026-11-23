"""Settings, read once from environment variables (and an optional `.env` file).

Every variable is documented in `.env.example`. Secrets are `SecretStr`, so they never show up
in logs, reprs or error messages.
"""

from __future__ import annotations

import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

CommaList = Annotated[list[str], NoDecode]


class Transport(StrEnum):
    STDIO = "stdio"
    HTTP = "http"


class SheetsBackendKind(StrEnum):
    GOOGLE = "google"
    MEMORY = "memory"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Postgres -------------------------------------------------------------------------
    database_url: SecretStr | None = Field(
        default=None, description="Connection string for the READ-ONLY role."
    )
    allowed_schemas: CommaList = Field(default_factory=lambda: ["public"])
    allowed_tables: CommaList = Field(
        default_factory=list,
        description="Empty = all tables in ALLOWED_SCHEMAS. Entries: table or schema.table",
    )
    query_timeout_ms: int = Field(default=5000, ge=100, le=120_000)
    max_rows: int = Field(default=500, ge=1, le=10_000)
    db_pool_max_size: int = Field(default=5, ge=1, le=50)

    # --- Google Sheets --------------------------------------------------------------------
    sheets_backend: SheetsBackendKind = SheetsBackendKind.GOOGLE
    google_service_account_json: SecretStr | None = Field(
        default=None, description="Path to the service-account key file, or the JSON itself."
    )
    sheets_memory_file: Path | None = Field(
        default=None, description="JSON file loaded by the in-memory Sheets backend (demo/tests)."
    )
    allowed_sheet_ids: CommaList = Field(default_factory=list)
    sheets_timeout_s: float = Field(default=10.0, gt=0, le=120)
    sheets_max_retries: int = Field(default=4, ge=0, le=10)

    # --- Behaviour ------------------------------------------------------------------------
    read_only: bool = True

    # --- Transport ------------------------------------------------------------------------
    transport: Transport = Transport.STDIO
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8765, ge=1, le=65535)
    public_url: str | None = Field(
        default=None,
        description="Public base URL of this server (resource identifier for OAuth metadata).",
    )
    http_allowed_hosts: CommaList = Field(
        default_factory=list,
        description="Extra Host header values accepted (DNS-rebinding protection).",
    )

    # --- OAuth (remote mode) --------------------------------------------------------------
    oauth_issuer: str | None = None
    oauth_audience: str | None = None
    oauth_jwks_url: str | None = Field(
        default=None, description="Optional. Defaults to the issuer's OIDC discovery jwks_uri."
    )
    rate_limit_per_min: int = Field(default=60, ge=1, le=100_000)

    # --- Audit / observability ------------------------------------------------------------
    audit_log_path: Path | None = Field(
        default=None, description="Empty = audit lines go to stdout (http) or stderr (stdio)."
    )
    redact_args: bool = True
    log_level: str = "INFO"
    sentry_dsn: SecretStr | None = None

    @field_validator(
        "allowed_schemas",
        "allowed_tables",
        "allowed_sheet_ids",
        "http_allowed_hosts",
        mode="before",
    )
    @classmethod
    def _split_commas(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_schemas", "allowed_tables")
    @classmethod
    def _lowercase_identifiers(cls, value: list[str]) -> list[str]:
        return [item.lower() for item in value]

    @field_validator("database_url", "google_service_account_json", "sentry_dsn", mode="before")
    @classmethod
    def _empty_secret_is_none(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator(
        "audit_log_path",
        "sheets_memory_file",
        "oauth_issuer",
        "oauth_audience",
        "oauth_jwks_url",
        "public_url",
        mode="before",
    )
    @classmethod
    def _empty_is_none(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _check_remote_mode(self) -> Settings:
        if self.transport is Transport.HTTP:
            missing = [
                name
                for name, val in (
                    ("OAUTH_ISSUER", self.oauth_issuer),
                    ("OAUTH_AUDIENCE", self.oauth_audience),
                )
                if not val
            ]
            if missing:
                raise ValueError(
                    "TRANSPORT=http requires OAuth: set "
                    + " and ".join(missing)
                    + ". The HTTP transport never runs without bearer-token validation."
                )
        if not self.allowed_schemas:
            raise ValueError("ALLOWED_SCHEMAS must list at least one schema")
        return self

    @property
    def resource_url(self) -> str:
        """The OAuth resource identifier: the public URL of the MCP endpoint."""
        base = self.public_url or f"http://localhost:{self.http_port}"
        return base.rstrip("/") + "/mcp"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
