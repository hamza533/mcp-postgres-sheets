"""Google Sheets backends.

* `GoogleSheetsBackend` — the real Sheets API v4 through a service account, with a per-request
  timeout and retries with exponential backoff + jitter on 429 / 5xx / network errors.
* `MemorySheetsBackend` — an in-memory spreadsheet loaded from JSON. Used by the tests, the
  evaluation and anyone who wants to try the server without a Google account
  (`SHEETS_BACKEND=memory`).

Both implement the same async `SheetsBackend` protocol. Writes always use
`valueInputOption=RAW`, so a value like ``=IMPORTXML(...)`` is stored as text and never evaluated.

Idempotency (write tools require an `idempotency_key`): the key is hashed and stored as
developer metadata on the rows it wrote, so a retry — even one that reaches a different server
replica — finds the marker and returns the original result instead of writing twice.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import socket
import threading
import time
import weakref
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Protocol

from mcp_postgres_sheets.config import Settings, SheetsBackendKind
from mcp_postgres_sheets.errors import (
    BlockedError,
    InvalidInputError,
    NotFoundError,
    RateLimitedError,
    SafeToolError,
    TimeoutError_,
    UnavailableError,
)

log = logging.getLogger(__name__)

Cell = str | int | float | bool | None
Grid = list[list[Cell]]

IDEMPOTENCY_METADATA_KEY = "mcp_idempotency"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


# --- A1 notation ----------------------------------------------------------------------------

_CELLS = re.compile(r"^\$?[A-Za-z]{0,3}\$?[0-9]{0,7}(?::\$?[A-Za-z]{0,3}\$?[0-9]{0,7})?$")
_CELL = re.compile(r"^\$?(?P<col>[A-Za-z]{0,3})\$?(?P<row>[0-9]{0,7})$")


def col_to_index(letters: str) -> int:
    """A → 0, Z → 25, AA → 26."""
    index = 0
    for ch in letters.upper():
        index = index * 26 + (ord(ch) - 64)
    return index - 1


def index_to_col(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


@dataclass(frozen=True)
class A1Range:
    tab: str | None
    start_col: int | None = None  # 0-based, inclusive; None = from column A
    start_row: int | None = None  # 0-based, inclusive; None = from row 1
    end_col: int | None = None  # inclusive; None = to the last column
    end_row: int | None = None  # inclusive; None = to the last row

    def with_tab(self, tab: str) -> A1Range:
        return A1Range(tab, self.start_col, self.start_row, self.end_col, self.end_row)

    def a1(self) -> str:
        tab = quote_tab(self.tab) if self.tab else ""
        if (
            self.start_col is None
            and self.start_row is None
            and self.end_col is None
            and self.end_row is None
        ):
            return tab
        start = (index_to_col(self.start_col) if self.start_col is not None else "A") + (
            str(self.start_row + 1) if self.start_row is not None else ""
        )
        end = (index_to_col(self.end_col) if self.end_col is not None else "") + (
            str(self.end_row + 1) if self.end_row is not None else ""
        )
        cells = start if end == start else f"{start}:{end}" if end else start
        return f"{tab}!{cells}" if tab else cells


def quote_tab(tab: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_]+", tab):
        return tab
    return "'" + tab.replace("'", "''") + "'"


def parse_a1(text: str) -> A1Range:
    """Parse `Tab!A1:C10`, `'My tab'!A:C`, `A2:B`, `Tab` … Raises InvalidInputError.

    Like the Sheets API, a bare token that looks like a cell reference (`B2`, `A:C`) is a range
    on the first tab; anything else without `!` is a tab name.
    """
    raw = text.strip()
    if not raw or len(raw) > 300:
        raise InvalidInputError(f"Invalid A1 range: {text!r}. Example: Leads!A1:D20")
    tab: str | None = None
    cells = raw
    if raw.startswith("'"):
        m = re.match(r"^'((?:[^']|'')+)'(?:!(.*))?$", raw)
        if not m:
            raise InvalidInputError(
                f"Invalid A1 range: {text!r}. Quote tab names like 'My tab'!A1:B2"
            )
        tab, cells = m.group(1).replace("''", "'"), m.group(2) or ""
    elif "!" in raw:
        tab, cells = raw.rsplit("!", 1)
    elif not _CELLS.match(raw):
        return A1Range(tab=raw)
    if not cells:
        return A1Range(tab=tab)
    if not _CELLS.match(cells):
        raise InvalidInputError(f"Invalid A1 range: {text!r}. Example: Leads!A1:D20")
    refs: list[tuple[int | None, int | None]] = []
    for part in cells.split(":"):
        cell = _CELL.match(part)
        if not cell or not (cell.group("col") or cell.group("row")):
            raise InvalidInputError(f"Invalid A1 range: {text!r}")
        col = col_to_index(cell.group("col")) if cell.group("col") else None
        row = int(cell.group("row")) - 1 if cell.group("row") else None
        if row is not None and row < 0:
            raise InvalidInputError(f"Invalid A1 range: {text!r} (rows start at 1)")
        refs.append((col, row))
    c1, r1 = refs[0]
    c2, r2 = refs[-1]
    if c1 is not None and c2 is not None and c2 < c1:
        c1, c2 = c2, c1
    if r1 is not None and r2 is not None and r2 < r1:
        r1, r2 = r2, r1
    return A1Range(tab=tab, start_col=c1, start_row=r1, end_col=c2, end_row=r2)


# --- Results ------------------------------------------------------------------------------


@dataclass(frozen=True)
class TabMeta:
    title: str
    index: int
    rows: int
    columns: int


@dataclass(frozen=True)
class SpreadsheetMeta:
    title: str
    tabs: list[TabMeta]


@dataclass(frozen=True)
class WriteResult:
    updated_range: str
    updated_rows: int
    updated_cells: int
    duplicate: bool = False


class SheetsBackend(Protocol):
    async def get_metadata(self, sheet_id: str) -> SpreadsheetMeta: ...
    async def read_range(self, sheet_id: str, a1: str) -> tuple[str, Grid]: ...
    async def append_rows(
        self, sheet_id: str, tab: str, rows: Grid, idempotency_key: str
    ) -> WriteResult: ...
    async def update_range(
        self, sheet_id: str, a1: str, values: Grid, idempotency_key: str
    ) -> WriteResult: ...
    async def check(self) -> None: ...
    async def aclose(self) -> None: ...


def hash_key(idempotency_key: str, operation: str, sheet_id: str) -> str:
    raw = f"{operation}\x00{sheet_id}\x00{idempotency_key}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


class _RecentResults:
    """Process-local idempotency cache (fast path; the durable record lives in the sheet)."""

    def __init__(self, size: int = 2048) -> None:
        self._items: OrderedDict[str, WriteResult] = OrderedDict()
        self._size = size
        self._lock = threading.Lock()

    def get(self, key: str) -> WriteResult | None:
        with self._lock:
            hit = self._items.get(key)
            return (
                None
                if hit is None
                else WriteResult(hit.updated_range, hit.updated_rows, hit.updated_cells, True)
            )

    def put(self, key: str, result: WriteResult) -> None:
        with self._lock:
            self._items[key] = result
            self._items.move_to_end(key)
            while len(self._items) > self._size:
                self._items.popitem(last=False)


# --- In-memory backend ----------------------------------------------------------------------


@dataclass
class _MemSheet:
    title: str
    tabs: dict[str, Grid] = field(default_factory=dict)


def _trim(grid: Grid) -> Grid:
    rows = [list(r) for r in grid]
    for r in rows:
        while r and (r[-1] is None or r[-1] == ""):
            r.pop()
    while rows and not rows[-1]:
        rows.pop()
    return rows


class MemorySheetsBackend:
    """Spreadsheets held in memory. Behaves like the API for the subset the tools use."""

    def __init__(self, spreadsheets: dict[str, _MemSheet]) -> None:
        self._sheets = spreadsheets
        self._lock = asyncio.Lock()
        self._done = _RecentResults()

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> MemorySheetsBackend:
        sheets = {
            sid: _MemSheet(
                title=s["title"],
                tabs={name: [list(r) for r in rows] for name, rows in s["tabs"].items()},
            )
            for sid, s in data["spreadsheets"].items()
        }
        return cls(sheets)

    @classmethod
    def from_file(cls, path: Path | None) -> MemorySheetsBackend:
        if path is None:
            text = (
                resources.files("mcp_postgres_sheets")
                .joinpath("data/sheets_demo.json")
                .read_text("utf-8")
            )
        else:
            text = path.read_text(encoding="utf-8")
        return cls.from_json(json.loads(text))

    def _sheet(self, sheet_id: str) -> _MemSheet:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            raise NotFoundError(f"Spreadsheet {sheet_id} was not found.")
        return sheet

    def _tab(self, sheet: _MemSheet, tab: str | None) -> tuple[str, Grid]:
        name = tab or next(iter(sheet.tabs))
        if name not in sheet.tabs:
            raise NotFoundError(
                f"Tab {name!r} was not found. Use sheets_list_tabs to see the tabs."
            )
        return name, sheet.tabs[name]

    async def get_metadata(self, sheet_id: str) -> SpreadsheetMeta:
        sheet = self._sheet(sheet_id)
        tabs = [
            TabMeta(
                title=name,
                index=i,
                rows=max(len(g), 1000),
                columns=max((len(r) for r in g), default=0) or 26,
            )
            for i, (name, g) in enumerate(sheet.tabs.items())
        ]
        return SpreadsheetMeta(title=sheet.title, tabs=tabs)

    async def read_range(self, sheet_id: str, a1: str) -> tuple[str, Grid]:
        rng = parse_a1(a1)
        name, grid = self._tab(self._sheet(sheet_id), rng.tab)
        r0, r1 = rng.start_row or 0, rng.end_row if rng.end_row is not None else len(grid) - 1
        c0 = rng.start_col or 0
        width = max((len(r) for r in grid), default=0)
        c1 = rng.end_col if rng.end_col is not None else width - 1
        out = [list(row[c0 : c1 + 1]) for row in grid[r0 : r1 + 1]]
        resolved = A1Range(name, c0, r0, c1 if c1 >= c0 else c0, r1 if r1 >= r0 else r0).a1()
        return resolved, _trim(out)

    async def append_rows(
        self, sheet_id: str, tab: str, rows: Grid, idempotency_key: str
    ) -> WriteResult:
        key = hash_key(idempotency_key, "append", sheet_id)
        async with self._lock:
            if (hit := self._done.get(key)) is not None:
                return hit
            name, grid = self._tab(self._sheet(sheet_id), tab)
            trimmed = _trim(grid)
            del grid[len(trimmed) :]
            start = len(grid)
            grid.extend([list(r) for r in rows])
            width = max((len(r) for r in rows), default=1)
            result = WriteResult(
                updated_range=A1Range(name, 0, start, width - 1, start + len(rows) - 1).a1(),
                updated_rows=len(rows),
                updated_cells=sum(len(r) for r in rows),
            )
            self._done.put(key, result)
            return result

    async def update_range(
        self, sheet_id: str, a1: str, values: Grid, idempotency_key: str
    ) -> WriteResult:
        key = hash_key(idempotency_key, "update", sheet_id)
        async with self._lock:
            if (hit := self._done.get(key)) is not None:
                return hit
            rng = parse_a1(a1)
            name, grid = self._tab(self._sheet(sheet_id), rng.tab)
            r0, c0 = rng.start_row or 0, rng.start_col or 0
            for i, row in enumerate(values):
                while len(grid) <= r0 + i:
                    grid.append([])
                target = grid[r0 + i]
                while len(target) < c0 + len(row):
                    target.append(None)
                for j, cell in enumerate(row):
                    target[c0 + j] = cell
            width = max((len(r) for r in values), default=1)
            result = WriteResult(
                updated_range=A1Range(name, c0, r0, c0 + width - 1, r0 + len(values) - 1).a1(),
                updated_rows=len(values),
                updated_cells=sum(len(r) for r in values),
            )
            self._done.put(key, result)
            return result

    async def check(self) -> None:
        return None

    async def aclose(self) -> None:
        return None


# --- Google backend -------------------------------------------------------------------------


def load_service_account_info(value: str) -> dict[str, Any]:
    """GOOGLE_SERVICE_ACCOUNT_JSON is either a path to the key file or the JSON itself."""
    text = value.strip()
    if not text.startswith("{"):
        path = Path(text).expanduser()
        if not path.is_file():
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON points to a file that does not exist")
        text = path.read_text(encoding="utf-8")
    info = json.loads(text)
    if info.get("type") != "service_account":
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not a service-account key")
    return dict(info)


def _http_status(exc: BaseException) -> int | None:
    resp = getattr(exc, "resp", None)
    status = getattr(resp, "status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _retry_after(exc: BaseException) -> float | None:
    resp = getattr(exc, "resp", None)
    value = resp.get("retry-after") if isinstance(resp, dict) else None
    try:
        return min(float(value), 60.0) if value is not None else None
    except (TypeError, ValueError):
        return None


def _google_message(exc: BaseException) -> str:
    content = getattr(exc, "content", b"")
    try:
        data = json.loads(content.decode() if isinstance(content, bytes) else content)
        return str(data["error"]["message"])[:300]
    except (ValueError, KeyError, TypeError, AttributeError):
        return ""


class GoogleSheetsBackend:
    """Sheets API v4 via a service account. Blocking client calls run in worker threads."""

    def __init__(
        self,
        *,
        credentials: Any,
        service_account_email: str | None,
        timeout_s: float,
        max_retries: int,
        http_factory: Callable[[], Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        from googleapiclient.discovery import build

        self._credentials = credentials
        self.service_account_email = service_account_email
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._sleep = sleep
        self._http_factory = http_factory or self._authorized_http
        # Static discovery document bundled with the client: no network call at start-up.
        self._service = build(
            "sheets", "v4", http=self._http_factory(), cache_discovery=False, static_discovery=True
        )
        self._done = _RecentResults()
        self._key_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> GoogleSheetsBackend:
        from google.oauth2 import service_account

        if settings.google_service_account_json is None:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")
        info = load_service_account_info(settings.google_service_account_json.get_secret_value())
        creds = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
            info, scopes=[SHEETS_SCOPE]
        )
        return cls(
            credentials=creds,
            service_account_email=info.get("client_email"),
            timeout_s=settings.sheets_timeout_s,
            max_retries=settings.sheets_max_retries,
        )

    def _authorized_http(self) -> Any:
        import google_auth_httplib2
        import httplib2

        return google_auth_httplib2.AuthorizedHttp(
            self._credentials, http=httplib2.Http(timeout=self._timeout)
        )

    def _execute(self, request: Any, what: str, *, retry_unsure: bool = True) -> Any:
        """Run one API request with retries. A fresh HTTP object per attempt (httplib2 is not thread-safe).

        `retry_unsure=False` is for requests that are not idempotent (append): a timeout or a 5xx
        may come *after* Google applied the change, so only a 429 (rejected, nothing done) is
        retried.
        """
        attempt = 0
        while True:
            try:
                return request.execute(http=self._http_factory(), num_retries=0)
            except Exception as exc:
                status = _http_status(exc)
                if retry_unsure:
                    transient = status in RETRY_STATUSES or (
                        status is None
                        and isinstance(
                            exc, socket.timeout | TimeoutError | ConnectionError | OSError
                        )
                    )
                else:
                    transient = status == 429
                if transient and attempt < self._max_retries:
                    delay = _retry_after(exc) or min(30.0, 0.5 * 2**attempt) * random.uniform(
                        0.5, 1.5
                    )
                    log.warning(
                        "sheets %s: transient error (status=%s), retry %d in %.1fs",
                        what,
                        status,
                        attempt + 1,
                        delay,
                    )
                    self._sleep(delay)
                    attempt += 1
                    continue
                raise self._map_error(exc, status) from None

    def _map_error(self, exc: BaseException, status: int | None) -> SafeToolError:
        detail = _google_message(exc)
        if status == 403:
            who = (
                f" Share it with {self.service_account_email}."
                if self.service_account_email
                else ""
            )
            return BlockedError(f"the service account cannot access this spreadsheet.{who}")
        if status == 404:
            return NotFoundError("Spreadsheet not found. Check the sheet ID.")
        if status == 400:
            return InvalidInputError(
                f"Google Sheets rejected the request: {detail or 'bad request'}"
            )
        if status == 429:
            return RateLimitedError("Google Sheets quota exceeded. Try again in a minute.")
        if status is not None and status >= 500:
            return UnavailableError("Google Sheets is temporarily unavailable. Try again shortly.")
        if isinstance(exc, socket.timeout | TimeoutError):
            return TimeoutError_(f"Google Sheets did not answer within {self._timeout:.0f} s.")
        return UnavailableError("Could not reach Google Sheets.")

    async def _run(self, fn: Callable[[], Any]) -> Any:
        return await asyncio.to_thread(fn)

    async def get_metadata(self, sheet_id: str) -> SpreadsheetMeta:
        req = self._service.spreadsheets().get(
            spreadsheetId=sheet_id,
            fields="properties.title,sheets.properties(title,index,gridProperties(rowCount,columnCount))",
        )
        data = await self._run(lambda: self._execute(req, "get"))
        tabs = [
            TabMeta(
                title=s["properties"]["title"],
                index=s["properties"].get("index", i),
                rows=s["properties"].get("gridProperties", {}).get("rowCount", 0),
                columns=s["properties"].get("gridProperties", {}).get("columnCount", 0),
            )
            for i, s in enumerate(data.get("sheets", []))
        ]
        return SpreadsheetMeta(title=data.get("properties", {}).get("title", ""), tabs=tabs)

    async def read_range(self, sheet_id: str, a1: str) -> tuple[str, Grid]:
        req = (
            self._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=a1,
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
        )
        data = await self._run(lambda: self._execute(req, "read"))
        return data.get("range", a1), [list(r) for r in data.get("values", [])]

    async def _find_marker(self, sheet_id: str, key: str) -> WriteResult | None:
        req = (
            self._service.spreadsheets()
            .developerMetadata()
            .search(
                spreadsheetId=sheet_id,
                body={
                    "dataFilters": [
                        {
                            "developerMetadataLookup": {
                                "metadataKey": IDEMPOTENCY_METADATA_KEY,
                                "metadataValue": key,
                            }
                        }
                    ]
                },
            )
        )
        data = await self._run(lambda: self._execute(req, "idempotency lookup"))
        for match in data.get("matchedDeveloperMetadata", []):
            meta = match.get("developerMetadata", {})
            dim = meta.get("location", {}).get("dimensionRange", {})
            start, end = dim.get("startIndex", 0), dim.get("endIndex", 0)
            return WriteResult(
                updated_range=f"rows {start + 1}-{end}",
                updated_rows=end - start,
                updated_cells=0,
                duplicate=True,
            )
        return None

    async def _tab_gid(self, sheet_id: str, tab: str) -> int:
        req = self._service.spreadsheets().get(
            spreadsheetId=sheet_id, fields="sheets.properties(sheetId,title)"
        )
        data = await self._run(lambda: self._execute(req, "get"))
        for s in data.get("sheets", []):
            if s["properties"]["title"] == tab:
                return int(s["properties"]["sheetId"])
        raise NotFoundError(f"Tab {tab!r} was not found. Use sheets_list_tabs to see the tabs.")

    async def _mark(self, sheet_id: str, tab: str, start_row: int, end_row: int, key: str) -> None:
        """Store the durable idempotency marker. Never raises: the rows are already written."""
        try:
            gid = await self._tab_gid(sheet_id, tab)
        except SafeToolError:
            log.warning("could not store idempotency marker for sheet write (tab lookup failed)")
            return
        body = {
            "requests": [
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": IDEMPOTENCY_METADATA_KEY,
                            "metadataValue": key,
                            "visibility": "PROJECT",
                            "location": {
                                "dimensionRange": {
                                    "sheetId": gid,
                                    "dimension": "ROWS",
                                    "startIndex": start_row,
                                    "endIndex": end_row + 1,
                                }
                            },
                        }
                    }
                }
            ]
        }
        req = self._service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body)
        try:
            await self._run(lambda: self._execute(req, "idempotency marker"))
        except SafeToolError:
            # The rows are written; only the durable marker failed. The in-process cache still
            # protects retries to this replica. Log it, don't fail a write that succeeded.
            log.warning("could not store idempotency marker for sheet write")

    async def append_rows(
        self, sheet_id: str, tab: str, rows: Grid, idempotency_key: str
    ) -> WriteResult:
        key = hash_key(idempotency_key, "append", sheet_id)
        # One in-flight append per key in this process: a retry that arrives while the first
        # call is still running waits for it and then finds its result in the cache.
        lock = self._key_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._key_locks[key] = lock
        async with lock:
            return await self._append_once(sheet_id, tab, rows, key)

    async def _append_once(self, sheet_id: str, tab: str, rows: Grid, key: str) -> WriteResult:
        if (hit := self._done.get(key)) is not None:
            return hit
        if (marker := await self._find_marker(sheet_id, key)) is not None:
            return marker
        req = (
            self._service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range=quote_tab(tab),
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                includeValuesInResponse=False,
                body={"values": rows},
            )
        )
        try:
            data = await self._run(lambda: self._execute(req, "append", retry_unsure=False))
        except (TimeoutError_, UnavailableError) as exc:
            raise type(exc)(
                f"{exc.message} Google did not confirm the append, so the rows may or may not have "
                "been written. Read the end of the tab with sheets_read_range before retrying."
            ) from None
        updates = data.get("updates", {})
        updated_range = updates.get("updatedRange", "")
        result = WriteResult(
            updated_range=updated_range,
            updated_rows=int(updates.get("updatedRows", len(rows))),
            updated_cells=int(updates.get("updatedCells", 0)),
        )
        self._done.put(key, result)  # before the marker: a retry to this process is now safe
        try:
            written = parse_a1(updated_range) if updated_range else None
        except InvalidInputError:
            written = None
        if written is not None and written.start_row is not None:
            end = written.end_row if written.end_row is not None else written.start_row
            # Google reports the tab's real title; the caller's spelling may differ in case.
            await self._mark(sheet_id, written.tab or tab, written.start_row, end, key)
        return result

    async def update_range(
        self, sheet_id: str, a1: str, values: Grid, idempotency_key: str
    ) -> WriteResult:
        # Writing the same values to the same cells twice gives the same sheet, so updates are
        # naturally idempotent; the key still short-circuits retries so they cost no API call.
        key = hash_key(idempotency_key, "update", sheet_id)
        if (hit := self._done.get(key)) is not None:
            return hit
        req = (
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=sheet_id, range=a1, valueInputOption="RAW", body={"values": values}
            )
        )
        data = await self._run(lambda: self._execute(req, "update"))
        result = WriteResult(
            updated_range=data.get("updatedRange", a1),
            updated_rows=int(data.get("updatedRows", len(values))),
            updated_cells=int(data.get("updatedCells", 0)),
        )
        self._done.put(key, result)
        return result

    async def check(self) -> None:
        """Readiness: the service-account credentials can obtain an access token."""
        import google_auth_httplib2
        import httplib2

        request = google_auth_httplib2.Request(httplib2.Http(timeout=self._timeout))
        try:
            await asyncio.to_thread(self._credentials.refresh, request)
        except Exception:
            raise UnavailableError(
                "Google service-account credentials could not get a token."
            ) from None

    async def aclose(self) -> None:
        return None


def build_sheets_backend(settings: Settings) -> SheetsBackend | None:
    if settings.sheets_backend is SheetsBackendKind.MEMORY:
        return MemorySheetsBackend.from_file(settings.sheets_memory_file)
    if settings.google_service_account_json is None:
        return None
    return GoogleSheetsBackend.from_settings(settings)
