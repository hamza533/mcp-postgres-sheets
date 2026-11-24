from __future__ import annotations

import pytest

from mcp_postgres_sheets.errors import BlockedError
from mcp_postgres_sheets.sql_guard import AllowList, check_sql, search_path_sql

ALLOW = AllowList(schemas=("public",))

GOOD = [
    "SELECT 1",
    "select 1;",
    "SELECT * FROM orders",
    "SELECT * FROM public.orders WHERE status = 'paid'",
    "SELECT c.full_name, sum(oi.quantity * oi.unit_price) AS revenue FROM customers c "
    "JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id "
    "GROUP BY c.full_name ORDER BY revenue DESC LIMIT 5",
    "WITH q AS (SELECT * FROM orders WHERE ordered_at > now() - interval '90 days') SELECT count(*) FROM q",
    "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 10) SELECT * FROM r",
    "SELECT id FROM orders UNION SELECT id FROM customers",
    "SELECT id FROM orders INTERSECT SELECT customer_id FROM orders",
    "SELECT * FROM generate_series(1, 10)",
    "SELECT date_trunc('month', ordered_at), count(*) FROM orders GROUP BY 1",
    "SELECT extract(quarter FROM ordered_at), to_char(ordered_at, 'YYYY-MM') FROM orders",
    "SELECT string_agg(name, ', ') FILTER (WHERE active) FROM products",
    "SELECT rank() OVER (PARTITION BY category ORDER BY unit_price DESC) FROM products",
    "SELECT * FROM customers c, LATERAL (SELECT * FROM orders o WHERE o.customer_id = c.id LIMIT 1) x",
    "SELECT * FROM orders WHERE id = 1 /* a comment; with a semicolon */",
    "SELECT 'DROP TABLE customers; --' AS harmless_text",
    "SELECT $$; DROP TABLE x; $$ AS dollar_quoted_text",
    "SELECT email FROM customers WHERE email LIKE '%@example.com'",
]

BAD = [
    ("DROP TABLE customers", "single SELECT"),
    ("SELECT 1; SELECT 2", "2 statements"),
    ("WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d", "DELETE"),
    ("SELECT * INTO t FROM orders", "INTO"),
    ("SELECT * FROM orders FOR SHARE", "locking"),
    ("SELECT pg_sleep(1)", "pg_sleep"),
    ("SELECT * FROM internal.employees", "ALLOWED_SCHEMAS"),
    ("SELECT * FROM pg_roles", "system catalog"),
    ("SELECT * FROM shop.public.orders", "cross-database"),
    ("VALUES (1)", "single SELECT"),
    ("", "empty"),
    ("SELEC * FRM orders", "single SELECT"),
    ("SELECT 1\x00", "NUL"),
]


@pytest.mark.parametrize("sql", GOOD)
def test_accepts_reads(sql: str) -> None:
    assert check_sql(sql, ALLOW).sql


@pytest.mark.parametrize(("sql", "reason"), BAD)
def test_rejects(sql: str, reason: str) -> None:
    with pytest.raises(BlockedError, match=reason):
        check_sql(sql, ALLOW)


def test_rejection_message_is_for_the_ai() -> None:
    with pytest.raises(BlockedError) as info:
        check_sql("DROP TABLE customers;", ALLOW)
    assert str(info.value) == "Rejected: only a single SELECT is allowed (got DROP)"


def test_trailing_semicolon_is_stripped() -> None:
    assert check_sql("SELECT 1 ;  ", ALLOW).sql == "SELECT 1"


def test_reports_tables() -> None:
    checked = check_sql(
        "WITH x AS (SELECT * FROM orders) SELECT * FROM x JOIN public.customers c ON true", ALLOW
    )
    assert set(checked.tables) == {"orders", "public.customers"}


def test_table_allow_list() -> None:
    allow = AllowList(schemas=("public",), tables=("orders", "public.order_items"))
    check_sql("SELECT * FROM orders JOIN order_items ON true", allow)
    check_sql("SELECT * FROM public.orders", allow)
    with pytest.raises(BlockedError, match="ALLOWED_TABLES"):
        check_sql("SELECT * FROM customers", allow)
    with pytest.raises(BlockedError, match="ALLOWED_TABLES"):
        check_sql("SELECT * FROM public.customers", allow)


def test_cte_only_hides_tables_in_its_own_scope() -> None:
    allow = AllowList(schemas=("public",), tables=("orders",))
    # A CTE defined inside a subquery is not visible outside it: the outer name is a real table.
    with pytest.raises(BlockedError, match="employees"):
        check_sql(
            "SELECT * FROM (WITH employees AS (SELECT 1) SELECT * FROM employees) s, employees",
            allow,
        )
    # Without RECURSIVE a CTE body only sees the CTEs before it; a forward reference is a table.
    with pytest.raises(BlockedError, match="customers"):
        check_sql(
            "WITH a AS (SELECT * FROM customers), customers AS (SELECT 1) SELECT * FROM a", allow
        )
    # Still allowed: normal, chained and recursive CTEs, and a CTE used inside a subquery.
    check_sql("WITH a AS (SELECT * FROM orders), b AS (SELECT * FROM a) SELECT * FROM b", allow)
    check_sql(
        "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 3) SELECT * FROM r",
        allow,
    )
    check_sql("WITH a AS (SELECT * FROM orders) SELECT * FROM (SELECT * FROM a) s", allow)
    check_sql("WITH a AS (SELECT * FROM orders) SELECT * FROM a UNION SELECT * FROM a", allow)


def test_unqualified_table_must_be_unambiguous() -> None:
    allow = AllowList(
        schemas=("public", "internal"), tables=("public.customers", "internal.orders")
    )
    # Postgres would resolve `orders` to public.orders (first on search_path), which is not allowed.
    with pytest.raises(BlockedError, match=r"internal.orders"):
        check_sql("SELECT * FROM orders", allow)
    check_sql("SELECT * FROM internal.orders", allow)
    # A bare entry allows the name in every schema, so the unqualified form stays fine.
    check_sql("SELECT * FROM orders", AllowList(schemas=("public", "internal"), tables=("orders",)))


def test_quoted_identifiers_keep_case() -> None:
    allow = AllowList(schemas=("public",))
    with pytest.raises(BlockedError, match="Public"):
        check_sql('SELECT * FROM "Public".orders', allow)
    check_sql("SELECT * FROM PUBLIC.ORDERS", allow)  # unquoted folds to lower case


def test_multiple_schemas() -> None:
    allow = AllowList(schemas=("public", "sales"))
    check_sql("SELECT * FROM sales.leads", allow)
    assert allow.default_schema == "public"


def test_search_path_quotes_identifiers() -> None:
    assert search_path_sql(["public", 'we"ird']) == 'SET LOCAL search_path = "public", "we""ird"'
