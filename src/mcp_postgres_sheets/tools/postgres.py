"""Postgres tools: postgres_list_tables, postgres_describe_table, postgres_query.

No `from __future__ import annotations` here: FastMCP builds each tool's JSON schema from the
real annotation objects.
"""

import time
from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from mcp_postgres_sheets.db import Database, to_jsonable, unique_column_names
from mcp_postgres_sheets.errors import (
    BlockedError,
    InvalidInputError,
    NotFoundError,
    UnavailableError,
)
from mcp_postgres_sheets.sql_guard import MAX_SQL_LENGTH, check_sql
from mcp_postgres_sheets.tools._runtime import GuardedFastMCP, ServerState

SCOPE_DB_READ = "db:read"

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


# --- Output models -------------------------------------------------------------------------


class TableInfo(BaseModel):
    schema_name: str
    name: str
    kind: str = Field(description="table, view, materialized view or foreign table.")
    estimated_rows: int | None = Field(description="Planner estimate (not exact); null for views.")
    comment: str | None


class ListTablesResult(BaseModel):
    tables: list[TableInfo]
    row_count: int = Field(description="Number of tables returned.")


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    default: str | None
    comment: str | None


class ForeignKey(BaseModel):
    columns: list[str]
    references_table: str = Field(description="schema.table the key points to.")
    references_columns: list[str]


class DescribeTableResult(BaseModel):
    schema_name: str
    name: str
    kind: str
    comment: str | None
    columns: list[ColumnInfo]
    primary_key: list[str]
    foreign_keys: list[ForeignKey] = Field(
        description="Keys in this table referencing other tables."
    )
    referenced_by: list[ForeignKey] = Field(
        description="Keys in other tables referencing this one (columns are in the other table)."
    )
    row_count: int = Field(description="Number of columns.")


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int = Field(description="Rows returned (after the row cap).")
    truncated: bool = Field(description="True if the query produced more rows than max_rows.")
    max_rows: int
    duration_ms: float


# --- Catalog SQL (fixed, parameterised; never built from user input) ---------------------

_KINDS = "CASE c.relkind WHEN 'r' THEN 'table' WHEN 'p' THEN 'table' WHEN 'v' THEN 'view' \
WHEN 'm' THEN 'materialized view' WHEN 'f' THEN 'foreign table' END"

LIST_TABLES_SQL = f"""
SELECT n.nspname, c.relname, {_KINDS},
       CASE WHEN c.relkind IN ('r', 'p', 'm') AND c.reltuples >= 0 THEN c.reltuples::bigint END,
       obj_description(c.oid, 'pg_class')
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = ANY(%s)
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
  AND NOT c.relispartition
  AND has_table_privilege(c.oid, 'SELECT')
ORDER BY n.nspname, c.relname
"""  # noqa: S608 - _KINDS is a constant

FIND_TABLE_SQL = f"""
SELECT c.oid, {_KINDS}, obj_description(c.oid, 'pg_class')
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = %s AND c.relname = %s
  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
  AND has_table_privilege(c.oid, 'SELECT')
"""  # noqa: S608

COLUMNS_SQL = """
SELECT a.attname, format_type(a.atttypid, a.atttypmod), NOT a.attnotnull,
       pg_get_expr(d.adbin, d.adrelid), col_description(a.attrelid, a.attnum)
FROM pg_attribute a
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE a.attrelid = %s AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum
"""

_KEY_COLS = """(SELECT array_agg(a.attname ORDER BY k.ord)
   FROM unnest({keys}) WITH ORDINALITY AS k(attnum, ord)
   JOIN pg_attribute a ON a.attrelid = {rel} AND a.attnum = k.attnum)"""

PRIMARY_KEY_SQL = f"""
SELECT {_KEY_COLS.format(keys="con.conkey", rel="con.conrelid")}
FROM pg_constraint con WHERE con.conrelid = %s AND con.contype = 'p'
"""  # noqa: S608

FOREIGN_KEYS_SQL = f"""
SELECT {_KEY_COLS.format(keys="con.conkey", rel="con.conrelid")},
       fn.nspname, fc.relname,
       {_KEY_COLS.format(keys="con.confkey", rel="con.confrelid")},
       tn.nspname, tc.relname
FROM pg_constraint con
JOIN pg_class fc ON fc.oid = con.confrelid JOIN pg_namespace fn ON fn.oid = fc.relnamespace
JOIN pg_class tc ON tc.oid = con.conrelid  JOIN pg_namespace tn ON tn.oid = tc.relnamespace
WHERE con.contype = 'f' AND (con.conrelid = %s OR con.confrelid = %s)
ORDER BY con.conname
"""  # noqa: S608


def _fold(name: str) -> str:
    """Like Postgres: unquoted identifiers fold to lower case, "Quoted" ones keep their case."""
    name = name.strip()
    if len(name) >= 2 and name.startswith('"') and name.endswith('"'):
        return name[1:-1].replace('""', '"')
    return name.lower()


def _split_table(table: str, schema: str | None, state: ServerState) -> tuple[str, str]:
    table = table.strip()
    if schema is None and "." in table:
        schema, table = table.split(".", 1)
    schema = _fold(schema) if schema else state.allow.default_schema
    table = _fold(table)
    if not state.allow.schema_allowed(schema):
        raise BlockedError(
            f"schema {schema} is not in ALLOWED_SCHEMAS ({', '.join(state.allow.schemas)})"
        )
    if not state.allow.table_allowed(schema, table):
        raise BlockedError(f"table {schema}.{table} is not in ALLOWED_TABLES")
    return schema, table


def _db(state: ServerState) -> Database:
    if state.db is None:
        raise UnavailableError("Postgres is not configured on this server (DATABASE_URL is empty).")
    return state.db


def register_postgres_tools(mcp: GuardedFastMCP, state: ServerState) -> None:
    s = state.settings
    schemas = ", ".join(s.allowed_schemas)

    async def postgres_list_tables(
        schema: Annotated[
            str | None,
            Field(
                description=f"Only list this schema. One of: {schemas}. Omit to list all allowed schemas."
            ),
        ] = None,
    ) -> ListTablesResult:
        if schema is not None and not state.allow.schema_allowed(schema):
            raise BlockedError(f"schema {schema} is not in ALLOWED_SCHEMAS ({schemas})")
        wanted = [schema] if schema else list(state.allow.schemas)
        rows = await _db(state).fetch_all(LIST_TABLES_SQL, (wanted,))
        tables = [
            TableInfo(schema_name=r[0], name=r[1], kind=r[2], estimated_rows=r[3], comment=r[4])
            for r in rows
            if state.allow.table_allowed(r[0], r[1])
        ]
        return ListTablesResult(tables=tables, row_count=len(tables))

    async def postgres_describe_table(
        table: Annotated[
            str,
            Field(
                description="Table or view name, optionally schema-qualified (e.g. orders or public.orders).",
                min_length=1,
                max_length=130,
            ),
        ],
        schema: Annotated[
            str | None,
            Field(
                description=f"Schema of the table. Defaults to {s.allowed_schemas[0]}.",
                max_length=63,
            ),
        ] = None,
    ) -> DescribeTableResult:
        schema_name, table_name = _split_table(table, schema, state)
        db = _db(state)
        found = await db.fetch_all(FIND_TABLE_SQL, (schema_name, table_name))
        if not found:
            raise NotFoundError(
                f"Table {schema_name}.{table_name} was not found. Use postgres_list_tables to see what exists."
            )
        oid, kind, comment = found[0]
        columns = [
            ColumnInfo(name=r[0], type=r[1], nullable=r[2], default=r[3], comment=r[4])
            for r in await db.fetch_all(COLUMNS_SQL, (oid,))
        ]
        pk_rows = await db.fetch_all(PRIMARY_KEY_SQL, (oid,))
        primary_key = list(pk_rows[0][0]) if pk_rows and pk_rows[0][0] else []
        outgoing: list[ForeignKey] = []
        incoming: list[ForeignKey] = []
        for cols, ref_schema, ref_table, ref_cols, own_schema, own_table in await db.fetch_all(
            FOREIGN_KEYS_SQL, (oid, oid)
        ):
            if (own_schema, own_table) == (schema_name, table_name):
                if state.allow.table_allowed(ref_schema, ref_table):
                    outgoing.append(
                        ForeignKey(
                            columns=list(cols),
                            references_table=f"{ref_schema}.{ref_table}",
                            references_columns=list(ref_cols),
                        )
                    )
            elif state.allow.table_allowed(own_schema, own_table):
                incoming.append(
                    ForeignKey(
                        columns=list(cols),
                        references_table=f"{own_schema}.{own_table}",
                        references_columns=list(ref_cols),
                    )
                )
        return DescribeTableResult(
            schema_name=schema_name,
            name=table_name,
            kind=kind,
            comment=comment,
            columns=columns,
            primary_key=primary_key,
            foreign_keys=outgoing,
            referenced_by=incoming,
            row_count=len(columns),
        )

    async def postgres_query(
        sql: Annotated[
            str,
            Field(
                description="Exactly one PostgreSQL SELECT statement (WITH … SELECT and UNION are fine).",
                min_length=1,
                max_length=MAX_SQL_LENGTH,
            ),
        ],
        max_rows: Annotated[
            int | None,
            Field(
                description=f"Return at most this many rows (1 to {s.max_rows}). Defaults to {s.max_rows}.",
                ge=1,
                le=s.max_rows,
            ),
        ] = None,
    ) -> QueryResult:
        checked = check_sql(sql, state.allow)
        limit = max_rows or s.max_rows
        if limit > s.max_rows:  # defence in depth; the schema already enforces this
            raise InvalidInputError(f"max_rows must be at most {s.max_rows}")
        started = time.perf_counter()
        names, rows, truncated = await _db(state).run_select(checked.sql, limit)
        columns = unique_column_names(names)
        records = [dict(zip(columns, (to_jsonable(v) for v in row), strict=True)) for row in rows]
        return QueryResult(
            columns=columns,
            rows=records,
            row_count=len(records),
            truncated=truncated,
            max_rows=limit,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )

    mcp.add_guarded_tool(
        postgres_list_tables,
        name="postgres_list_tables",
        scope=SCOPE_DB_READ,
        title="List Postgres tables",
        description=(
            f"List the tables and views the AI may query in the allowed schemas ({schemas}), with "
            "approximate row counts and table comments. Call this first to discover what data exists, "
            "then postgres_describe_table for column details."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    mcp.add_guarded_tool(
        postgres_describe_table,
        name="postgres_describe_table",
        scope=SCOPE_DB_READ,
        title="Describe a Postgres table",
        description=(
            "Describe one table or view: columns with types, nullability, defaults and comments, the "
            "primary key, foreign keys to other tables, and foreign keys from other tables (use these "
            "to write correct JOINs). Call before writing a query against a table you haven't seen."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
    mcp.add_guarded_tool(
        postgres_query,
        name="postgres_query",
        scope=SCOPE_DB_READ,
        title="Run a read-only SQL query",
        description=(
            "Run ONE read-only PostgreSQL SELECT and return the rows as JSON objects. "
            f"Only tables in the allowed schemas ({schemas}) can be read. Rejected: anything that is not "
            "a single SELECT (INSERT/UPDATE/DELETE/DDL, multiple statements, SELECT INTO, FOR UPDATE), "
            "system catalogs (pg_*), and unsafe functions (pg_sleep, pg_read_file, dblink, set_config…). "
            f"Results are capped at {s.max_rows} rows (truncated=true means more rows exist) and the query "
            f"is cancelled after {s.query_timeout_ms} ms, so aggregate in SQL (GROUP BY, ORDER BY … LIMIT) "
            "rather than fetching raw rows. Use postgres_describe_table first to get exact column names."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
    )
