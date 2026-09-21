import pytest

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
    ddl = (
        'CREATE TABLE "my table" (id int);\n'
        + "CREATE TABLE " + tick + "order items" + tick + " (id int);\n"
        + "CREATE TABLE [select] (id int);"
    )
    document = md.sql_ddl_to_markdown(ddl)

    assert 'Table: "my table"' in document
    assert "Table: " + tick + "order items" + tick in document
    assert "Table: [select]" in document
    assert md.markdown_to_sql_ddl(document) == ddl

def test_sql_snapshot_lists_qualified_and_escaped_quoted_names():
    ddl = 'CREATE TABLE "schema"."my table" (id int);\nCREATE TABLE "my ""table""" (id int);'
    document = md.sql_ddl_to_markdown(ddl)

    assert 'Table: "schema"."my table"' in document
    assert 'Table: "my ""table"""' in document
    assert md.markdown_to_sql_ddl(document) == ddl


def test_markdown_table_statistics_reports_only_fully_numeric_columns():
    source = "| name | score |\n| --- | --- |\n| a | 1 |\n| b | 3 |\n"

    assert md.markdown_table_statistics(source) == {
        "rows": 2,
        "columns": 2,
        "headers": ["name", "score"],
        "numeric_columns": {
            "score": {"count": 2, "min": 1.0, "max": 3.0, "mean": 2.0, "median": 2.0}
        },
    }


def test_markdown_table_statistics_excludes_nan_and_inf_spellings():
    """float() happily parses "nan"/"inf"/"infinity" -- a text column
    using those words is not numeric data and must not be aggregated."""
    source = "| name | flag |\n| --- | --- |\n| a | nan |\n| b | NaN |\n"
    assert md.markdown_table_statistics(source)["numeric_columns"] == {}

    inf_source = "| name | score |\n| --- | --- |\n| a | 1 |\n| b | inf |\n"
    assert md.markdown_table_statistics(inf_source)["numeric_columns"] == {}


def test_markdown_table_statistics_rejects_duplicate_headers():
    """numeric_columns is keyed by header text, which can't represent two
    columns of the same name losslessly -- same contract as
    markdown_table_to_records, which also raises on duplicate headers."""
    source = "| score | score |\n| --- | --- |\n| 1 | 100 |\n| 3 | 200 |\n"
    with pytest.raises(ValueError, match="unique"):
        md.markdown_table_statistics(source)


def test_sql_snapshot_normalizes_crlf_to_lf():
    ddl = "CREATE TABLE t (id int);\r\n"
    document = md.sql_ddl_to_markdown(ddl)

    assert "\r" not in document
    assert md.markdown_to_sql_ddl(document) == "CREATE TABLE t (id int);\n"


def test_sql_snapshot_preserves_normalized_trailing_newline_count():
    ddl = "CREATE TABLE t (id int);\r\n\r\n"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(ddl)) == (
        "CREATE TABLE t (id int);\n\n"
    )


def test_sql_snapshot_normalizes_lone_cr_to_lf():
    ddl = "CREATE TABLE t (id int);\rCREATE TABLE u (id int);\r"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(ddl)) == (
        "CREATE TABLE t (id int);\nCREATE TABLE u (id int);\n"
    )



def test_structured_markdown_round_trip_nested_json_compatible_values():
    value = {
        "user": {"name": "妙本", "active": True, "score": 1.5},
        "tags": ["ai", "a|b", "line\nbreak"],
        "empty_map": {},
        "empty_list": [],
        "none": None,
        "count": 3,
    }

    document = md.structured_to_markdown(value)

    assert "<!-- markdown.py:structured-v1 -->" in document
    assert md.markdown_to_structured(document) == value


def test_structured_markdown_round_trip_root_scalars_and_containers():
    for value in [None, True, 0, -3, 1.25, "日本語|\\n", [], {}]:
        assert md.markdown_to_structured(md.structured_to_markdown(value)) == value


def test_structured_markdown_rejects_non_string_mapping_keys():
    with pytest.raises(TypeError, match="string keys"):
        md.structured_to_markdown({1: "value"})


def test_structured_markdown_rejects_non_finite_float():
    with pytest.raises(ValueError):
        md.structured_to_markdown(float("nan"))


def test_markdown_to_structured_rejects_noncanonical_headers():
    source = "| key | value |\n| --- | --- |\n| a | 1 |\n"
    with pytest.raises(ValueError, match="canonical"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_type_mismatch():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | int | \"text\" |\n"
    )
    with pytest.raises(ValueError, match="type mismatch"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_bad_parent_reference():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
        "| 1 | 9 | \"x\" | int | 1 |\n"
    )
    with pytest.raises(ValueError, match="earlier node"):
        md.markdown_to_structured(source)



def test_markdown_to_structured_requires_format_marker():
    source = (
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
    )
    with pytest.raises(ValueError, match="marker"):
        md.markdown_to_structured(source)


def test_structured_markdown_round_trip_tricky_keys_and_values():
    value = {
        "a|b": "pipe|value",
        "quote\"key": "backslash\\value",
        "日本語": ["改行\n入り", "", False],
    }
    assert md.markdown_to_structured(md.structured_to_markdown(value)) == value


def test_structured_markdown_rejects_tuple_and_bytes():
    with pytest.raises(TypeError):
        md.structured_to_markdown(("a", "b"))
    with pytest.raises(TypeError):
        md.structured_to_markdown(b"bytes")


def test_structured_markdown_rejects_positive_and_negative_infinity():
    for value in [float("inf"), float("-inf")]:
        with pytest.raises(ValueError):
            md.structured_to_markdown(value)


def test_markdown_to_structured_rejects_duplicate_mapping_key():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
        "| 1 | 0 | \"x\" | int | 1 |\n"
        "| 2 | 0 | \"x\" | int | 2 |\n"
    )
    with pytest.raises(ValueError, match="duplicate key"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_out_of_order_list_slot():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | list |  |\n"
        "| 1 | 0 | 1 | int | 1 |\n"
    )
    with pytest.raises(ValueError, match="contiguous"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_unknown_type_tag():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | datetime | \"2026-09-21T00:00:00\" |\n"
    )
    with pytest.raises(ValueError, match="Unknown structured node type"):
        md.markdown_to_structured(source)
