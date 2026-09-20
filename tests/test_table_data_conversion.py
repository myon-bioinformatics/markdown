"""P2 table data conversions and CJK display-width contracts."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_csv_table_csv_round_trip_handles_quotes_and_pipes() -> None:
    source = 'name,note\n妙本,"a, b | c"\n'
    table = md.csv_to_markdown_table(source)

    assert "妙本" in table
    assert "a, b \\| c" in table
    assert md.markdown_table_to_csv(table) == source


def test_csv_table_csv_round_trip_preserves_backslashes() -> None:
    source = 'path,note\n"C:\\work\\demo","literal \\| pipe"\n'
    result = md.markdown_table_to_csv(md.csv_to_markdown_table(source))
    assert list(csv.reader(io.StringIO(result))) == list(csv.reader(io.StringIO(source)))


def test_aligned_table_uses_cjk_display_width() -> None:
    table = md.aligned_table(["項目", "value"], [["猫", "1"], ["wide", "二"]])
    lines = table.splitlines()

    assert lines[0] == "| 項目 | value |"
    assert lines[2] == "| 猫   | 1     |"
    assert lines[3] == "| wide | 二    |"


def test_table_to_rows_ignores_fenced_examples_and_pads_short_rows() -> None:
    source = "```markdown\n| ignored | table |\n| --- | --- |\n| x | y |\n```\n| a | b |\n| --- | --- |\n| 1 |\n"
    assert md.markdown_table_to_rows(source) == (["a", "b"], [["1", ""]])


def test_table_to_records_rejects_duplicate_headers() -> None:
    source = "| a | a |\n| --- | --- |\n| 1 | 2 |\n"
    with pytest.raises(ValueError, match="unique"):
        md.markdown_table_to_records(source)


def test_malformed_or_missing_table_degrades_to_empty_data() -> None:
    assert md.markdown_table_to_rows("| a | b |\n| nope |\n") == ([], [])
    assert md.csv_to_markdown_table("") == ""
