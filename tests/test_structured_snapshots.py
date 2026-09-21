from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_json_and_redis_snapshots_are_lossless_without_connection() -> None:
    value = {"user": {"name": "妙本"}, "tags": ["ai", "md"], "ttl": 60}
    assert md.markdown_to_json(md.json_to_markdown(value)) == value
    assert md.markdown_to_json(md.redis_snapshot_to_markdown(value)) == value


def test_sql_ddl_is_documented_and_returned_without_dialect_interpretation() -> None:
    ddl = "CREATE TABLE app.users (id bigint PRIMARY KEY);\nCREATE TABLE audit.log (id uuid);\n"
    document = md.sql_ddl_to_markdown(ddl)
    assert "Table: app.users" in document and "Table: audit.log" in document
    assert md.markdown_to_sql_ddl(document) == ddl


def test_sql_ddl_round_trip_is_byte_exact_on_trailing_newlines() -> None:
    """The round trip must not add, drop, or collapse trailing newlines --
    "lossless" means byte-exact, not "normalized to one trailing newline"."""
    no_trailing = "CREATE TABLE x (a int);"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(no_trailing)) == no_trailing

    many_trailing = "CREATE TABLE x (a int);\n\n\n"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(many_trailing)) == many_trailing


def test_sql_ddl_table_name_outline_keeps_quoted_identifiers_with_spaces() -> None:
    ddl = 'CREATE TABLE "My Table" (id int);\nCREATE TABLE `Order Items` (id int);\n'
    document = md.sql_ddl_to_markdown(ddl)
    assert 'Table: "My Table"' in document
    assert "Table: `Order Items`" in document
    assert md.markdown_to_sql_ddl(document) == ddl
