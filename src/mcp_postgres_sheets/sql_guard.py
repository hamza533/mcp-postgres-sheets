"""SQL check (safety layer 3): accept exactly one read-only SELECT over allow-listed tables.

The read-only database role and the READ ONLY transaction are what actually guarantee nothing
is written. This check exists to reject bad queries *early*, with a clear message the AI can act
on, and to enforce the schema/table allow-lists and the unsafe-function deny-list, which the
database alone does not know about.

Anything sqlglot cannot parse is rejected: when in doubt, say no.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

from mcp_postgres_sheets.errors import BlockedError

logging.getLogger("sqlglot").setLevel(logging.ERROR)

MAX_SQL_LENGTH = 20_000

# Statement / clause node types that must never appear anywhere in the tree (including CTEs
# and subqueries). Looked up by name so a sqlglot upgrade that renames one fails closed.
_FORBIDDEN_NODE_NAMES = (
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "AlterColumn",
    "TruncateTable", "Copy", "Command", "Set", "SetItem", "Transaction", "Commit", "Rollback",
    "Into", "Lock", "Use", "Grant", "Revoke", "Analyze", "Comment", "Pragma", "LoadData",
    "Refresh", "Cache", "Uncache", "Describe", "Kill", "Summarize",
)  # fmt: skip
_FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = tuple(
    getattr(exp, name) for name in _FORBIDDEN_NODE_NAMES if hasattr(exp, name)
)

# Roots we accept: a SELECT, or set operations (UNION / INTERSECT / EXCEPT) of SELECTs.
_SET_OPERATIONS: tuple[type[exp.Expression], ...] = tuple(
    getattr(exp, name) for name in ("Union", "Intersect", "Except") if hasattr(exp, name)
)

# Functions that can sleep, read files, reach other servers, change settings, run nested SQL
# strings, take locks or touch sequences. Matched on the lower-case function name.
_DENIED_FUNCTIONS = frozenset(
    {
        "current_setting", "set_config", "nextval", "setval", "currval", "lastval",
        "version", "inet_server_addr", "inet_server_port", "inet_client_addr",
        "query_to_xml", "query_to_xml_and_xmlschema", "query_to_xmlschema",
        "cursor_to_xml", "cursor_to_xmlschema", "table_to_xml", "table_to_xml_and_xmlschema",
        "table_to_xmlschema", "schema_to_xml", "schema_to_xml_and_xmlschema", "schema_to_xmlschema",
        "database_to_xml", "database_to_xml_and_xmlschema", "database_to_xmlschema",
        "txid_current", "txid_current_if_assigned",
    }
)  # fmt: skip
_DENIED_FUNCTION_PREFIXES = ("pg_", "lo_", "dblink", "xmlparse")

_UNQUOTED_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_$]*$")


@dataclass(frozen=True)
class AllowList:
    """Schemas/tables the AI may read. Names are compared like Postgres does (see `_ident`)."""

    schemas: tuple[str, ...]
    tables: tuple[str, ...] = ()  # empty = every table in `schemas`

    @property
    def default_schema(self) -> str:
        return self.schemas[0]

    def schema_allowed(self, schema: str) -> bool:
        return schema in self.schemas

    def table_allowed(self, schema: str, table: str) -> bool:
        if not self.schema_allowed(schema):
            return False
        if not self.tables:
            return True
        return table in self.tables or f"{schema}.{table}" in self.tables


@dataclass(frozen=True)
class CheckedQuery:
    sql: str
    tables: tuple[str, ...]  # schema-qualified where the query qualified them


def _ident(node: exp.Expression | str | None) -> str:
    """Postgres folds unquoted identifiers to lower case; quoted ones keep their case."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node.lower()
    if isinstance(node, exp.Identifier):
        return node.name if node.quoted else node.name.lower()
    return node.name.lower()


def _function_name(node: exp.Func) -> str:
    if isinstance(node, exp.Anonymous):
        return str(node.name).lower()
    return str(node.sql_name()).lower()  # type: ignore[no-untyped-call]


def _cte_names(tree: exp.Expression) -> set[str]:
    return {
        _ident(cte.args["alias"].this) for cte in tree.find_all(exp.CTE) if cte.args.get("alias")
    }


def _check_functions(tree: exp.Expression) -> None:
    for func in tree.find_all(exp.Func):
        name = _function_name(func)
        if name in _DENIED_FUNCTIONS or name.startswith(_DENIED_FUNCTION_PREFIXES):
            raise BlockedError(f"function {name}() is not allowed")


def _check_tables(tree: exp.Expression, allow: AllowList) -> tuple[str, ...]:
    ctes = _cte_names(tree)
    seen: list[str] = []
    for table in tree.find_all(exp.Table):
        name = _ident(table.this) if isinstance(table.this, exp.Identifier) else ""
        if not name:
            continue  # table functions, e.g. generate_series(); functions are checked separately
        catalog = _ident(table.args.get("catalog"))
        schema = _ident(table.args.get("db"))
        if catalog:
            raise BlockedError("cross-database references are not allowed")
        if not schema:
            if name in ctes:
                continue
            if name.startswith("pg_"):
                # Unqualified pg_* names resolve to pg_catalog before any allowed schema.
                raise BlockedError(f"system catalog {name} is not allowed")
            if allow.tables and not any(allow.table_allowed(s, name) for s in allow.schemas):
                raise BlockedError(f"table {name} is not in ALLOWED_TABLES")
            seen.append(name)
            continue
        if not allow.schema_allowed(schema):
            raise BlockedError(f"schema {schema} is not in ALLOWED_SCHEMAS")
        if not allow.table_allowed(schema, name):
            raise BlockedError(f"table {schema}.{name} is not in ALLOWED_TABLES")
        seen.append(f"{schema}.{name}")
    return tuple(dict.fromkeys(seen))


def _is_select_root(tree: exp.Expression) -> bool:
    if isinstance(tree, exp.Select):
        return True
    if _SET_OPERATIONS and isinstance(tree, _SET_OPERATIONS):
        return _is_select_root(tree.args["this"]) and _is_select_root(tree.args["expression"])
    if isinstance(tree, exp.Subquery):
        return _is_select_root(tree.this)
    return False


def check_sql(sql: str, allow: AllowList) -> CheckedQuery:
    """Return the query if it is a single safe SELECT, else raise `BlockedError`."""
    text = sql.strip()
    if not text:
        raise BlockedError("empty query")
    if len(text) > MAX_SQL_LENGTH:
        raise BlockedError(f"query is longer than {MAX_SQL_LENGTH} characters")
    if "\x00" in text:
        raise BlockedError("query contains a NUL byte")

    try:
        statements = [s for s in sqlglot.parse(text, dialect="postgres") if s is not None]
    except (ParseError, TokenError):
        raise BlockedError(
            "could not parse the query as PostgreSQL; only a single SELECT is allowed"
        ) from None

    if len(statements) != 1:
        raise BlockedError(f"only a single SELECT is allowed (found {len(statements)} statements)")
    tree = statements[0]

    if not _is_select_root(tree):
        kind = type(tree).__name__.upper()
        raise BlockedError(f"only a single SELECT is allowed (got {kind})")

    for node in tree.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            kind = type(node).__name__.upper()
            if kind == "INTO":
                raise BlockedError("SELECT … INTO creates a table and is not allowed")
            if kind == "LOCK":
                raise BlockedError("locking clauses (FOR UPDATE / FOR SHARE) are not allowed")
            raise BlockedError(f"{kind} is not allowed inside a query; only reads are permitted")

    _check_functions(tree)
    tables = _check_tables(tree, allow)
    return CheckedQuery(sql=text.rstrip().rstrip(";").rstrip(), tables=tables)


def quote_ident(name: str) -> str:
    """Quote an identifier for Postgres (used for SET LOCAL search_path)."""
    return '"' + name.replace('"', '""') + '"'


def search_path_sql(schemas: Iterable[str]) -> str:
    return "SET LOCAL search_path = " + ", ".join(quote_ident(s) for s in schemas)


def is_simple_identifier(name: str) -> bool:
    return bool(_UNQUOTED_IDENTIFIER.match(name))
