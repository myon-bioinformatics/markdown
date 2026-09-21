import markdown as md


def test_markdown_table_statistics_reports_numeric_columns_only():
    result = md.markdown_table_statistics(
        "| name | score |\n| --- | --- |\n| a | 1 |\n| b | 3 |\n"
    )

    assert result == {
        "rows": 2,
        "columns": 2,
        "headers": ["name", "score"],
        "numeric_columns": {
            "score": {"count": 2, "min": 1.0, "max": 3.0, "mean": 2.0, "median": 2.0}
        },
    }


def test_markdown_table_statistics_empty_table_is_a_small_snapshot():
    assert md.markdown_table_statistics("") == {
        "rows": 0, "columns": 0, "headers": [], "numeric_columns": {}
    }


def test_mixed_non_numeric_column_is_excluded_from_numeric_columns():
    """A column with even one non-numeric value stays out of numeric_columns
    entirely, per the docstring's "Empty or mixed columns are absent"."""
    result = md.markdown_table_statistics(
        "| name | score |\n| --- | --- |\n| a | 1 |\n| b | x |\n"
    )
    assert result["rows"] == 2
    assert result["numeric_columns"] == {}


def test_header_only_table_has_zero_rows_but_keeps_headers():
    result = md.markdown_table_statistics("| name | score |\n| --- | --- |\n")
    assert result == {
        "rows": 0,
        "columns": 2,
        "headers": ["name", "score"],
        "numeric_columns": {},
    }
