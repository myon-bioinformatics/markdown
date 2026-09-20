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
