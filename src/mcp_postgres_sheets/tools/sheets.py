"""Google Sheets tools: 3 read tools, and 2 write tools registered only when READ_ONLY=false.

No `from __future__ import annotations` here: FastMCP builds each tool's JSON schema from the
real annotation objects.
"""

from typing import Annotated, Any, Literal

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_postgres_sheets.db import to_jsonable
from mcp_postgres_sheets.errors import (
    BlockedError,
    InvalidInputError,
    NotFoundError,
    UnavailableError,
)
from mcp_postgres_sheets.sheets import (
    A1Range,
    Cell,
    SheetsBackend,
    WriteResult,
    col_to_index,
    parse_a1,
)
from mcp_postgres_sheets.tools._runtime import GuardedFastMCP, ServerState

SCOPE_SHEETS_READ = "sheets:read"
SCOPE_SHEETS_WRITE = "sheets:write"

MAX_WRITE_CELLS = 5000
MAX_CELL_CHARS = 50_000  # Google Sheets' own per-cell limit
MAX_SCAN_ROWS = 20_000  # sheets_find_rows reads at most this many rows

READ_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True
)
APPEND_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
)
UPDATE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True
)


# --- Output models -------------------------------------------------------------------------


class TabInfo(BaseModel):
    title: str
    index: int
    rows: int = Field(description="Grid rows (including empty ones).")
    columns: int


class ListTabsResult(BaseModel):
    sheet_id: str
    title: str
    tabs: list[TabInfo]
    row_count: int = Field(description="Number of tabs.")


class ReadRangeResult(BaseModel):
    sheet_id: str
    range: str = Field(description="The range actually read, in A1 notation.")
    values: list[list[Any]] = Field(
        description="Rows of cell values; trailing empty cells are omitted."
    )
    row_count: int
    truncated: bool = Field(description="True if the range had more rows than max_rows.")


class FoundRow(BaseModel):
    row_number: int = Field(
        description="1-based row number in the tab (use it to build an update range)."
    )
    values: dict[str, Any] = Field(description="Cell values keyed by the header in row 1.")


class FindRowsResult(BaseModel):
    sheet_id: str
    tab: str
    column: str = Field(description="Header of the column that was searched.")
    rows: list[FoundRow]
    row_count: int
    truncated: bool


class WriteRowsResult(BaseModel):
    sheet_id: str
    updated_range: str
    updated_rows: int
    updated_cells: int
    duplicate: bool = Field(
        description="True if this idempotency_key was already used: nothing was written again."
    )
    row_count: int


# --- Helpers -------------------------------------------------------------------------------


def _write_result(sheet_id: str, result: WriteResult) -> WriteRowsResult:
    return WriteRowsResult(
        sheet_id=sheet_id,
        updated_range=result.updated_range,
        updated_rows=result.updated_rows,
        updated_cells=result.updated_cells,
        duplicate=result.duplicate,
        row_count=0 if result.duplicate else result.updated_rows,
    )


def _check_values(values: list[list[Cell]]) -> None:
    cells = sum(len(r) for r in values)
    if cells == 0:
        raise InvalidInputError("Nothing to write: provide at least one non-empty row.")
    if cells > MAX_WRITE_CELLS:
        raise InvalidInputError(
            f"Too many cells in one call ({cells}); the limit is {MAX_WRITE_CELLS}."
        )
    for row in values:
        for cell in row:
            if isinstance(cell, str) and len(cell) > MAX_CELL_CHARS:
                raise InvalidInputError(f"A cell is longer than {MAX_CELL_CHARS} characters.")


def _column_index(header: list[Any], column: str) -> tuple[int, str]:
    wanted = column.strip().lower()
    for i, name in enumerate(header):
        if str(name).strip().lower() == wanted:
            return i, str(name)
    if column.isalpha() and len(column) <= 3:
        i = col_to_index(column)
        return i, str(header[i]) if i < len(header) else column.upper()
    names = ", ".join(str(h) for h in header if h not in (None, ""))
    raise NotFoundError(f"Column {column!r} not found in row 1. Headers: {names}")


def _matches(cell: Any, value: str, match: str, case_sensitive: bool) -> bool:
    if cell is None:
        return False
    text = str(cell)
    if isinstance(cell, float) and cell.is_integer():
        text = str(int(cell))
    if not case_sensitive:
        text, value = text.lower(), value.lower()
    return text == value if match == "exact" else value in text


def register_sheets_tools(mcp: GuardedFastMCP, state: ServerState) -> None:
    s = state.settings
    allowed = list(s.allowed_sheet_ids)
    allowed_text = ", ".join(allowed) if allowed else "none configured"

    def backend() -> SheetsBackend:
        if state.sheets is None:
            raise UnavailableError(
                "Google Sheets is not configured on this server (set GOOGLE_SERVICE_ACCOUNT_JSON)."
            )
        sheets: SheetsBackend = state.sheets
        return sheets

    def check_sheet(sheet_id: str) -> str:
        sheet_id = sheet_id.strip()
        if sheet_id not in allowed:
            raise BlockedError(
                f"spreadsheet {sheet_id} is not in ALLOWED_SHEET_IDS ({allowed_text})"
            )
        return sheet_id

    SheetId = Annotated[
        str,
        Field(
            description=(
                "Spreadsheet ID: the long ID in the sheet URL (docs.google.com/spreadsheets/d/<ID>/edit). "
                f"Allowed IDs: {allowed_text}."
            ),
            min_length=3,
            max_length=128,
            pattern=r"^\s*[A-Za-z0-9_-]+\s*$",
        ),
    ]
    MaxRows = Annotated[
        int | None,
        Field(
            description=f"Return at most this many rows (1 to {s.max_rows}). Defaults to {s.max_rows}.",
            ge=1,
            le=s.max_rows,
        ),
    ]
    Values = Annotated[
        list[list[Cell]],
        Field(
            description=(
                "Rows of cell values (strings, numbers, booleans or null). Values are stored exactly as "
                "given (RAW): text starting with '=' is NOT evaluated as a formula."
            ),
            min_length=1,
            max_length=s.max_rows,
        ),
    ]
    IdempotencyKey = Annotated[
        str,
        Field(
            description=(
                "A unique ID for this write, e.g. a UUID you generate. If the call is retried with the "
                "same key, nothing is written twice. Use a new key for each distinct write."
            ),
            min_length=8,
            max_length=128,
            pattern=r"^[A-Za-z0-9_.:-]+$",
        ),
    ]

    async def sheets_list_tabs(sheet_id: SheetId) -> ListTabsResult:
        sid = check_sheet(sheet_id)
        meta = await backend().get_metadata(sid)
        tabs = [
            TabInfo(title=t.title, index=t.index, rows=t.rows, columns=t.columns) for t in meta.tabs
        ]
        return ListTabsResult(sheet_id=sid, title=meta.title, tabs=tabs, row_count=len(tabs))

    async def sheets_read_range(
        sheet_id: SheetId,
        range: Annotated[
            str,
            Field(
                description="A1 range, e.g. Leads!A1:F50, 'Q3 plan'!A:C, or just a tab name (Leads) for the whole tab.",
                min_length=1,
                max_length=300,
            ),
        ],
        max_rows: MaxRows = None,
    ) -> ReadRangeResult:
        sid = check_sheet(sheet_id)
        parse_a1(range)  # validate early with a clear message
        limit = max_rows or s.max_rows
        resolved, values = await backend().read_range(sid, range.strip())
        truncated = len(values) > limit
        rows = [[to_jsonable(c) for c in row] for row in values[:limit]]
        return ReadRangeResult(
            sheet_id=sid, range=resolved, values=rows, row_count=len(rows), truncated=truncated
        )

    async def sheets_find_rows(
        sheet_id: SheetId,
        tab: Annotated[
            str, Field(description="Tab (sheet) name, e.g. Leads.", min_length=1, max_length=100)
        ],
        column: Annotated[
            str,
            Field(
                description="Column to search: its header text in row 1 (e.g. Email) or its letter (e.g. D).",
                min_length=1,
                max_length=200,
            ),
        ],
        value: Annotated[str, Field(description="Value to look for.", max_length=1000)],
        match: Annotated[
            Literal["exact", "contains"], Field(description="exact (default) or contains.")
        ] = "exact",
        case_sensitive: Annotated[bool, Field(description="Default false.")] = False,
        max_rows: MaxRows = None,
    ) -> FindRowsResult:
        sid = check_sheet(sheet_id)
        limit = max_rows or s.max_rows
        scan = A1Range(
            tab=tab.strip(),
            start_col=0,
            start_row=0,
            end_col=col_to_index("ZZ"),
            end_row=MAX_SCAN_ROWS,
        ).a1()
        _, values = await backend().read_range(sid, scan)
        if not values:
            raise NotFoundError(f"Tab {tab!r} is empty.")
        header = values[0]
        index, column_name = _column_index(header, column)
        headers = [
            str(h) if h not in (None, "") else f"column_{i + 1}" for i, h in enumerate(header)
        ]
        found: list[FoundRow] = []
        truncated = False
        for row_no, row in enumerate(values[1:], start=2):
            cell = row[index] if index < len(row) else None
            if _matches(cell, value, match, case_sensitive):
                if len(found) == limit:
                    truncated = True
                    break
                padded = list(row) + [None] * (len(headers) - len(row))
                found.append(
                    FoundRow(
                        row_number=row_no,
                        values={h: to_jsonable(v) for h, v in zip(headers, padded, strict=False)},
                    )
                )
        return FindRowsResult(
            sheet_id=sid,
            tab=tab.strip(),
            column=column_name,
            rows=found,
            row_count=len(found),
            truncated=truncated,
        )

    async def sheets_append_rows(
        sheet_id: SheetId,
        tab: Annotated[
            str, Field(description="Tab to append to, e.g. Leads.", min_length=1, max_length=100)
        ],
        rows: Values,
        idempotency_key: IdempotencyKey,
    ) -> WriteRowsResult:
        sid = check_sheet(sheet_id)
        _check_values(rows)
        result = await backend().append_rows(sid, tab.strip(), rows, idempotency_key)
        return _write_result(sid, result)

    async def sheets_update_range(
        sheet_id: SheetId,
        range: Annotated[
            str,
            Field(
                description="A1 range to overwrite, starting at a cell, e.g. Leads!E5 or Leads!E5:F5.",
                min_length=2,
                max_length=300,
            ),
        ],
        values: Values,
        idempotency_key: IdempotencyKey,
    ) -> WriteRowsResult:
        sid = check_sheet(sheet_id)
        _check_values(values)
        rng = parse_a1(range)
        if rng.tab is None or rng.start_row is None or rng.start_col is None:
            raise InvalidInputError("range must name a tab and a start cell, e.g. Leads!E5")
        width = max(len(r) for r in values)
        if rng.end_row is not None and rng.end_row - rng.start_row + 1 < len(values):
            raise InvalidInputError(f"{len(values)} rows do not fit in {range}")
        if rng.end_col is not None and rng.end_col - rng.start_col + 1 < width:
            raise InvalidInputError(f"{width} columns do not fit in {range}")
        result = await backend().update_range(sid, rng.a1(), values, idempotency_key)
        return _write_result(sid, result)

    mcp.add_guarded_tool(
        sheets_list_tabs,
        name="sheets_list_tabs",
        scope=SCOPE_SHEETS_READ,
        title="List spreadsheet tabs",
        description=(
            "List the tabs (sheets) of a Google Spreadsheet with their sizes. Call this first to learn tab "
            f"names before reading. Only allow-listed spreadsheets can be used: {allowed_text}."
        ),
        annotations=READ_ANNOTATIONS,
    )
    mcp.add_guarded_tool(
        sheets_read_range,
        name="sheets_read_range",
        title="Read a spreadsheet range",
        scope=SCOPE_SHEETS_READ,
        description=(
            "Read cell values from an A1 range of an allow-listed Google Spreadsheet (e.g. Leads!A1:F50, or "
            f"a tab name for the whole tab). Returns rows of values, capped at {s.max_rows} rows. Row 1 is "
            "usually the header."
        ),
        annotations=READ_ANNOTATIONS,
    )
    mcp.add_guarded_tool(
        sheets_find_rows,
        name="sheets_find_rows",
        title="Find rows in a spreadsheet",
        scope=SCOPE_SHEETS_READ,
        description=(
            "Find the rows of a tab where one column matches a value (exact or contains, case-insensitive "
            "by default). The column is named by its header in row 1 or its letter. Returns each matching "
            "row as an object keyed by header, with its row number."
        ),
        annotations=READ_ANNOTATIONS,
    )
    if s.read_only:
        return  # write tools are not registered at all: the AI never sees them
    mcp.add_guarded_tool(
        sheets_append_rows,
        name="sheets_append_rows",
        title="Append rows to a spreadsheet",
        scope=SCOPE_SHEETS_WRITE,
        description=(
            "Append rows after the last row of a tab in an allow-listed Google Spreadsheet. Give the values "
            "in the tab's column order (check the header with sheets_read_range first). Requires a unique "
            "idempotency_key so a retried call never adds the rows twice. Values are stored as-is; formulas "
            "are not evaluated."
        ),
        annotations=APPEND_ANNOTATIONS,
    )
    mcp.add_guarded_tool(
        sheets_update_range,
        name="sheets_update_range",
        title="Update a spreadsheet range",
        scope=SCOPE_SHEETS_WRITE,
        description=(
            "Overwrite the cells of an A1 range in an allow-listed Google Spreadsheet, starting at the "
            'range\'s first cell (e.g. Leads!E5 with [["Won"]]). Use sheets_find_rows to get the row number '
            "first. Requires a unique idempotency_key. Values are stored as-is; formulas are not evaluated."
        ),
        annotations=UPDATE_ANNOTATIONS,
    )
