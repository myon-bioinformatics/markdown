from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

BENCHMARK = ROOT / "fixtures" / "benchmark"


def test_table_generator_round_trips_to_html() -> None:
    src = md.table(["a", "b"], [[1, 2], [3, 4]])
    html = md.markdown_to_html(src)
    assert "<table>" in html
    assert "<thead>" in html
    assert "<th>a</th>" in html
    assert "<th>b</th>" in html
    assert "<tbody>" in html
    assert "<td>1</td>" in html
    assert "<td>2</td>" in html
    assert "<td>3</td>" in html
    assert "<td>4</td>" in html


def test_key_value_table_and_md_table_round_trip() -> None:
    kv = md.markdown_to_html(md.key_value_table({"mode": "train", "epochs": 10}))
    assert "<th>Key</th>" in kv
    assert "<td>mode</td>" in kv
    assert "<td>train</td>" in kv

    built = md.markdown_to_html(md.md_table(["name", "val"], ["loss", "0.01"]))
    assert "<th>name</th>" in built
    assert "<td>loss</td>" in built
    assert "<td>0.01</td>" in built


def test_short_row_is_padded_like_the_generator() -> None:
    src = md.table(["a", "b"], [[1]])
    html = md.markdown_to_html(src)
    assert html.count("<th>") == 2
    # One data row, two cells (the missing one is an empty <td></td>).
    assert "<tr><td>1</td><td></td></tr>" in html


def test_header_only_table_still_emits_thead_and_tbody() -> None:
    html = md.markdown_to_html("| a | b |\n| --- | --- |\n")
    assert "<table>" in html
    assert "<thead>" in html
    assert "<th>a</th>" in html
    assert "<tbody>" in html
    assert "<td>" not in html


def test_inline_formatting_inside_cells() -> None:
    src = "| x | y |\n| --- | --- |\n| **b** | `c` |\n"
    html = md.markdown_to_html(src)
    assert "<strong>b</strong>" in html
    assert "<code>c</code>" in html


def test_cell_html_is_escaped() -> None:
    html = md.markdown_to_html("| x |\n| --- |\n| <script>alert(1)</script> |\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_malformed_table_without_separator_stays_paragraph() -> None:
    """A pipe row with no ``| --- |`` delimiter is not a table.

    Documented degrade: the line is escaped/flattened as a paragraph, the
    same fallback as before tables were supported. No ``<table>`` is invented.
    """
    html = md.markdown_to_html("| a | b |\n| 1 | 2 |\n")
    assert "<table" not in html
    assert "<p>" in html
    assert "a" in html
    assert "b" in html


def test_separator_without_header_is_not_a_table() -> None:
    html = md.markdown_to_html("| --- | --- |\n| 1 | 2 |\n")
    assert "<table" not in html


def test_hyphen_run_shorter_than_three_is_not_a_delimiter() -> None:
    html = md.markdown_to_html("| a | b |\n| - | - |\n| 1 | 2 |\n")
    assert "<table" not in html


def test_alignment_colons_are_accepted_but_not_emitted() -> None:
    html = md.markdown_to_html(
        "| Left | Center | Right |\n"
        "| :--- | :---: | ---: |\n"
        "| a | b | c |\n"
    )
    assert "<table>" in html
    assert "<th>Left</th>" in html
    assert "align=" not in html


def test_optional_outer_pipes_and_paragraph_interrupt() -> None:
    html = md.markdown_to_html("before\na | b\n--- | ---\n1 | 2\nafter\n")
    assert html.startswith("<p>before</p>")
    assert html.endswith("<p>after</p>\n")
    assert "<th>a</th>" in html
    assert "<td>1</td>" in html


def test_list_item_with_pipes_is_not_a_table_header() -> None:
    html = md.markdown_to_html("- a | b\n| --- | --- |\n")
    assert "<table" not in html
    assert "<li>" in html


def test_fenced_table_example_stays_code() -> None:
    content = "```markdown\n| a | b |\n| --- | --- |\n| 1 | 2 |\n```\n"
    html = md.markdown_to_html(content)
    assert "<table" not in html
    assert "<pre><code" in html
    assert "| a | b |" in html


def test_github_docs_live_table_renders() -> None:
    content = (BENCHMARK / "github_docs_markdown.md").read_text(encoding="utf-8")
    html = md.markdown_to_html(content)
    assert "<table>" in html
    assert "<th>Style</th>" in html
    assert "<th>Syntax</th>" in html
    # Live strikethrough in the last cell of that table.
    assert "<del>This was mistaken text</del>" in html
    # The "Creating a table" fenced example stays code, not a second live table
    # of "First Header" as <th>.
    assert "First Header" in html
    assert "<th>First Header" not in html


def test_html_table_with_thead_becomes_gfm_pipes() -> None:
    html = (
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    )
    md_out = md.html_to_markdown(html)
    assert "| a | b |" in md_out
    assert "| --- | --- |" in md_out
    assert "| 1 | 2 |" in md_out


def test_markdown_table_round_trips_through_html_to_markdown() -> None:
    src = md.table(["a", "b"], [[1, 2], [3, 4]])
    back = md.html_to_markdown(md.markdown_to_html(src))
    assert "| a | b |" in back
    assert "| 1 | 2 |" in back
    assert "| 3 | 4 |" in back
    html = md.markdown_to_html(back)
    assert "<th>a</th>" in html
    assert "<td>3</td>" in html


def test_th_row_without_thead_is_still_a_header() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>x</th><th>y</th></tr><tr><td>1</td><td>2</td></tr></table>"
    )
    assert md_out.splitlines()[0] == "| x | y |"
    assert "| 1 | 2 |" in md_out


def test_headerless_table_uses_empty_header_so_rows_stay_data() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><td>a</td><td>b</td></tr><tr><td>1</td><td>2</td></tr></table>"
    )
    lines = [line for line in md_out.splitlines() if line.startswith("|")]
    assert lines[0] == "|  |  |"
    assert lines[1] == "| --- | --- |"
    assert "| a | b |" in md_out
    assert "| 1 | 2 |" in md_out


def test_pipe_in_cell_is_escaped() -> None:
    md_out = md.html_to_markdown(
        "<table><thead><tr><th>a</th></tr></thead>"
        "<tbody><tr><td>x|y</td></tr></tbody></table>"
    )
    assert r"| x\|y |" in md_out
    html = md.markdown_to_html(md_out)
    assert "<td>x|y</td>" in html


def test_inline_markup_inside_cells_survives() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>h</th></tr><tr><td><strong>b</strong> and <em>i</em></td></tr></table>"
    )
    assert "| **b** and *i* |" in md_out


def test_nested_table_flattens_into_the_cell() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>h</th></tr>"
        "<tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>"
    )
    assert md_out.count("| --- |") == 1
    assert "inner" in md_out
    assert "outer" in md_out


def test_colspan_is_ignored_as_a_single_cell() -> None:
    md_out = md.html_to_markdown(
        '<table><tr><th>a</th><th>b</th></tr>'
        '<tr><td colspan="2">wide</td></tr></table>'
    )
    assert "| wide |" in md_out or "| wide |  |" in md_out

