from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from googleapiclient.http import HttpMockSequence
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_postgres_sheets.config import Settings
from mcp_postgres_sheets.errors import (
    BlockedError,
    InvalidInputError,
    NotFoundError,
    RateLimitedError,
    UnavailableError,
)
from mcp_postgres_sheets.server import build_server
from mcp_postgres_sheets.sheets import (
    A1Range,
    GoogleSheetsBackend,
    MemorySheetsBackend,
    col_to_index,
    hash_key,
    index_to_col,
    load_service_account_info,
    parse_a1,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- A1 notation ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Leads!A1:C10", A1Range("Leads", 0, 0, 2, 9)),
        ("'Q3 plan'!B2", A1Range("Q3 plan", 1, 1, 1, 1)),
        ("'It''s'!A:C", A1Range("It's", 0, None, 2, None)),
        ("A2:B", A1Range(None, 0, 1, 1, None)),
        ("Leads", A1Range("Leads")),
        ("My tab", A1Range("My tab")),
        ("Leads!", A1Range("Leads")),
        ("Leads!2:5", A1Range("Leads", None, 1, None, 4)),
        ("Leads!$A$1:$B$2", A1Range("Leads", 0, 0, 1, 1)),
        ("Leads!C3:A1", A1Range("Leads", 0, 0, 2, 2)),
    ],
)
def test_parse_a1(text: str, expected: A1Range) -> None:
    assert parse_a1(text) == expected


@pytest.mark.parametrize(
    "text", ["", "Leads!A0", "Leads!A1:B2:C3", "Leads!A1;DROP", "'unterminated!A1"]
)
def test_parse_a1_rejects(text: str) -> None:
    with pytest.raises(InvalidInputError):
        parse_a1(text)


def test_column_letters_round_trip() -> None:
    for i in (0, 25, 26, 51, 701, 702):
        assert col_to_index(index_to_col(i)) == i
    assert index_to_col(27) == "AB"
    assert A1Range("My tab", 0, 4, 2, 9).a1() == "'My tab'!A5:C10"


def test_idempotency_hash_is_scoped() -> None:
    assert hash_key("k", "append", "s1") != hash_key("k", "append", "s2")
    assert hash_key("k", "append", "s1") != hash_key("k", "update", "s1")
    assert len(hash_key("k", "append", "s1")) == 24


def test_service_account_loader(tmp_path: Any) -> None:
    key = {"type": "service_account", "client_email": "bot@p.iam.gserviceaccount.com"}
    assert load_service_account_info(json.dumps(key)) == key
    path = tmp_path / "key.json"
    path.write_text(json.dumps(key))
    assert load_service_account_info(str(path))["client_email"] == key["client_email"]
    with pytest.raises(ValueError, match="does not exist"):
        load_service_account_info(str(tmp_path / "missing.json"))
    with pytest.raises(ValueError, match="not a service-account"):
        load_service_account_info('{"type": "authorized_user"}')


# --- Tools over MCP (memory backend) ----------------------------------------------------------


@pytest.fixture
async def client() -> AsyncIterator[ClientSession]:
    settings = Settings.model_validate(
        {
            "sheets_backend": "memory",
            "allowed_sheet_ids": "demo-sales-pipeline",
            "read_only": False,
            "max_rows": 50,
        }
    )
    mcp, _ = build_server(settings)
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        yield session


async def call(client: ClientSession, tool: str, **args: Any) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    text = " ".join(c.text for c in result.content if isinstance(c, TextContent))
    assert not result.isError, text
    assert result.structuredContent is not None
    return result.structuredContent


@pytest.mark.anyio
async def test_only_sheets_tools_without_database(client: ClientSession) -> None:
    names = {t.name for t in (await client.list_tools()).tools}
    assert names == {
        "sheets_list_tabs", "sheets_read_range", "sheets_find_rows",
        "sheets_append_rows", "sheets_update_range",
    }  # fmt: skip


@pytest.mark.anyio
async def test_read_only_hides_write_tools() -> None:
    settings = Settings.model_validate(
        {"sheets_backend": "memory", "allowed_sheet_ids": "demo-sales-pipeline"}
    )
    mcp, _ = build_server(settings)
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        names = {t.name for t in (await session.list_tools()).tools}
    assert names == {"sheets_list_tabs", "sheets_read_range", "sheets_find_rows"}


@pytest.mark.anyio
async def test_list_tabs_and_read(client: ClientSession) -> None:
    tabs = await call(client, "sheets_list_tabs", sheet_id="demo-sales-pipeline")
    assert [t["title"] for t in tabs["tabs"]] == ["Leads", "Targets", "Notes"]
    data = await call(
        client, "sheets_read_range", sheet_id="demo-sales-pipeline", range="Leads!A1:C3"
    )
    assert data["values"][0] == ["Lead ID", "Name", "Company"]
    assert data["row_count"] == 3 and data["range"] == "Leads!A1:C3"
    capped = await call(
        client, "sheets_read_range", sheet_id="demo-sales-pipeline", range="Leads", max_rows=5
    )
    assert capped["row_count"] == 5 and capped["truncated"] is True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Leads", "Leads!1:6"),  # whole tab → only limit + 1 rows are requested
        ("'Q3 plan'!A:C", "'Q3 plan'!A1:C6"),
        ("Leads!B10:D", "Leads!B10:D15"),
        ("Leads!A1:C3", "Leads!A1:C3"),  # already smaller than the limit: unchanged
        ("A2:B", "A2:B7"),
    ],
)
def test_read_range_requests_only_what_it_returns(text: str, expected: str) -> None:
    from mcp_postgres_sheets.tools.sheets import _bounded_range

    assert _bounded_range(parse_a1(text), text, 5) == expected


@pytest.mark.anyio
async def test_find_rows(client: ClientSession) -> None:
    data = await call(
        client,
        "sheets_find_rows",
        sheet_id="demo-sales-pipeline",
        tab="Leads",
        column="stage",
        value="won",
    )
    assert data["column"] == "Stage"
    assert data["row_count"] >= 1
    assert all(r["values"]["Stage"] == "Won" for r in data["rows"])
    assert all(r["row_number"] >= 2 for r in data["rows"])
    by_letter = await call(
        client,
        "sheets_find_rows",
        sheet_id="demo-sales-pipeline",
        tab="Leads",
        column="E",
        value="won",
    )
    assert by_letter["rows"] == data["rows"]
    result = await client.call_tool(
        "sheets_find_rows",
        {"sheet_id": "demo-sales-pipeline", "tab": "Leads", "column": "Nope", "value": "x"},
    )
    assert result.isError and "Headers: Lead ID" in result.content[0].text  # type: ignore[union-attr]


@pytest.mark.anyio
async def test_append_is_idempotent_and_raw(client: ClientSession) -> None:
    args = {
        "sheet_id": "demo-sales-pipeline",
        "tab": "Notes",
        "rows": [["2026-11-23", '=IMPORTXML("https://evil.example", "//a")']],
        "idempotency_key": "note-0001-abc",
    }
    first = await call(client, "sheets_append_rows", **args)
    assert first["duplicate"] is False and first["updated_range"] == "Notes!A2:B2"
    again = await call(client, "sheets_append_rows", **args)
    assert again["duplicate"] is True and again["row_count"] == 0
    notes = await call(client, "sheets_read_range", sheet_id="demo-sales-pipeline", range="Notes")
    assert len(notes["values"]) == 2  # header + one row, not two
    assert notes["values"][1][1].startswith("=IMPORTXML")  # stored as text


@pytest.mark.anyio
async def test_update_range(client: ClientSession) -> None:
    out = await call(
        client,
        "sheets_update_range",
        sheet_id="demo-sales-pipeline",
        range="Leads!E2",
        values=[["Won"]],
        idempotency_key="update-0001",
    )
    assert out["updated_range"] == "Leads!E2" and out["updated_cells"] == 1
    cell = await call(client, "sheets_read_range", sheet_id="demo-sales-pipeline", range="Leads!E2")
    assert cell["values"] == [["Won"]]
    too_big = await client.call_tool(
        "sheets_update_range",
        {
            "sheet_id": "demo-sales-pipeline",
            "range": "Leads!E2:E2",
            "values": [["a"], ["b"]],
            "idempotency_key": "update-0002",
        },
    )
    assert too_big.isError and "do not fit" in too_big.content[0].text  # type: ignore[union-attr]


# --- Google backend (HTTP mocked with the client library's own test helper) --------------------


def _google(
    responses: list[tuple[dict[str, str], str]], email: str | None = "bot@p.iam.gserviceaccount.com"
) -> tuple[GoogleSheetsBackend, list[float]]:
    http = HttpMockSequence(responses)
    sleeps: list[float] = []
    backend = GoogleSheetsBackend(
        credentials=None,
        service_account_email=email,
        timeout_s=5,
        max_retries=3,
        http_factory=lambda: http,
        sleep=sleeps.append,
    )
    return backend, sleeps


VALUES = json.dumps({"range": "Leads!A1:B2", "values": [["a", "b"], [1, 2]]})


@pytest.mark.anyio
async def test_google_retries_429_and_5xx_with_backoff() -> None:
    backend, sleeps = _google(
        [({"status": "429"}, "{}"), ({"status": "503"}, "{}"), ({"status": "200"}, VALUES)]
    )
    resolved, values = await backend.read_range("sheet", "Leads!A1:B2")
    assert resolved == "Leads!A1:B2" and values == [["a", "b"], [1, 2]]
    assert len(sleeps) == 2 and 0 < sleeps[0] < sleeps[1] * 2


@pytest.mark.anyio
async def test_google_honours_retry_after() -> None:
    backend, sleeps = _google(
        [({"status": "429", "retry-after": "7"}, "{}"), ({"status": "200"}, VALUES)]
    )
    await backend.read_range("sheet", "Leads!A1:B2")
    assert sleeps == [7.0]


@pytest.mark.anyio
async def test_google_gives_up_after_max_retries() -> None:
    backend, sleeps = _google([({"status": "429"}, "{}")] * 4)
    with pytest.raises(RateLimitedError):
        await backend.read_range("sheet", "A1")
    assert len(sleeps) == 3


@pytest.mark.anyio
async def test_google_403_explains_sharing() -> None:
    backend, sleeps = _google([({"status": "403"}, json.dumps({"error": {"message": "denied"}}))])
    with pytest.raises(BlockedError, match=r"Share it with bot@p.iam.gserviceaccount.com"):
        await backend.read_range("sheet", "A1")
    assert sleeps == []  # 403 is not retried


@pytest.mark.anyio
async def test_google_404_and_400() -> None:
    backend, _ = _google([({"status": "404"}, "{}")])
    with pytest.raises(NotFoundError):
        await backend.get_metadata("sheet")
    backend, _ = _google(
        [({"status": "400"}, json.dumps({"error": {"message": "Unable to parse range: X!A1"}}))]
    )
    with pytest.raises(InvalidInputError, match="Unable to parse range"):
        await backend.read_range("sheet", "X!A1")


@pytest.mark.anyio
async def test_google_append_writes_marker_and_detects_retry() -> None:
    appended = json.dumps(
        {"updates": {"updatedRange": "Leads!A31:B31", "updatedRows": 1, "updatedCells": 2}}
    )
    tabs = json.dumps({"sheets": [{"properties": {"sheetId": 7, "title": "Leads"}}]})
    backend, _ = _google(
        [
            ({"status": "200"}, json.dumps({})),  # marker search: nothing yet
            ({"status": "200"}, appended),  # values.append
            ({"status": "200"}, tabs),  # tab id lookup
            ({"status": "200"}, json.dumps({"replies": [{}]})),  # createDeveloperMetadata
        ]
    )
    result = await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert result.updated_range == "Leads!A31:B31" and not result.duplicate
    # Same key again: answered from the cache, no HTTP call (the mock sequence is exhausted).
    again = await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert again.duplicate is True


@pytest.mark.anyio
async def test_google_append_finds_durable_marker_from_another_replica() -> None:
    marker = {
        "matchedDeveloperMetadata": [
            {
                "developerMetadata": {
                    "location": {"dimensionRange": {"startIndex": 30, "endIndex": 31}}
                }
            }
        ]
    }
    backend, _ = _google([({"status": "200"}, json.dumps(marker))])
    result = await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert result.duplicate is True and result.updated_rows == 1


APPENDED = json.dumps(
    {"updates": {"updatedRange": "Leads!A31:B31", "updatedRows": 1, "updatedCells": 2}}
)
TABS = json.dumps({"sheets": [{"properties": {"sheetId": 7, "title": "Leads"}}]})
NO_MARKER = ({"status": "200"}, json.dumps({}))
MARKER_CREATED = ({"status": "200"}, json.dumps({"replies": [{}]}))


def _remaining(backend: GoogleSheetsBackend) -> int:
    return len(backend._http_factory()._iterable)


@pytest.mark.anyio
async def test_google_append_is_not_retried_after_an_ambiguous_failure() -> None:
    # A 503 (or a timeout) may arrive after Google wrote the rows: retrying could append twice.
    backend, sleeps = _google([NO_MARKER, ({"status": "503"}, "{}")])
    with pytest.raises(UnavailableError, match="may or may not have been written"):
        await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert sleeps == []


@pytest.mark.anyio
async def test_google_append_still_retries_429() -> None:
    backend, sleeps = _google(
        [
            NO_MARKER,
            ({"status": "429"}, "{}"),
            ({"status": "200"}, APPENDED),
            ({"status": "200"}, TABS),
            MARKER_CREATED,
        ]
    )
    result = await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert result.updated_rows == 1 and len(sleeps) == 1


@pytest.mark.anyio
async def test_google_append_succeeds_even_if_the_marker_cannot_be_stored() -> None:
    backend, _ = _google(
        [NO_MARKER, ({"status": "200"}, APPENDED), ({"status": "404"}, "{}")]  # tab lookup fails
    )
    result = await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert not result.duplicate
    again = await backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456")
    assert again.duplicate  # cached before the marker step, so a retry never writes again


@pytest.mark.anyio
async def test_google_append_marks_the_real_tab_title() -> None:
    # The caller wrote "leads"; Google resolved it to "Leads". The marker must still be stored.
    backend, _ = _google(
        [NO_MARKER, ({"status": "200"}, APPENDED), ({"status": "200"}, TABS), MARKER_CREATED]
    )
    await backend.append_rows("sheet", "leads", [["x", 1]], "key-123456")
    assert _remaining(backend) == 0  # createDeveloperMetadata was sent


@pytest.mark.anyio
async def test_google_concurrent_appends_with_one_key_write_once() -> None:
    backend, _ = _google(
        [NO_MARKER, ({"status": "200"}, APPENDED), ({"status": "200"}, TABS), MARKER_CREATED]
    )
    first, second = await asyncio.gather(
        backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456"),
        backend.append_rows("sheet", "Leads", [["x", 1]], "key-123456"),
    )
    assert sorted([first.duplicate, second.duplicate]) == [False, True]


@pytest.mark.anyio
async def test_memory_backend_unknown_sheet() -> None:
    backend = MemorySheetsBackend.from_file(None)
    with pytest.raises(NotFoundError):
        await backend.get_metadata("nope")
    with pytest.raises(NotFoundError, match="Tab 'Missing'"):
        await backend.read_range("demo-sales-pipeline", "Missing!A1")
