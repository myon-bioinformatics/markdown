import markdown as md


def test_json_and_redis_snapshots_are_lossless_without_connection():
    value = {"user": {"name": "妙本"}, "tags": ["ai", "md"], "ttl": 60}
    assert md.markdown_to_json(md.json_to_markdown(value)) == value
    assert md.markdown_to_json(md.redis_snapshot_to_markdown(value)) == value


def test_sql_snapshot_preserves_multiline_values_and_trailing_newlines():
    ddl = "CREATE TABLE logs (\n  id int,\n  note text\n);\n\n\n"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(ddl)) == ddl


def test_sql_snapshot_lists_quoted_and_bracket_table_names():
    tick = chr(96)
    ddl = 'CREATE TABLE "my table" (id int);\nCREATE TABLE ' + tick + "order items" + tick + '
 (id int);\nCREATE TABLE [select] (id int);'
    document = md.sql_ddl_to_markdown(ddl)

    assert 'Table: "my table"' in document
    assert "Table: " + tick + "order items" + tick in document
    assert "Table: [select]" in document
    assert md.markdown_to_sql_ddl(document) == ddl
