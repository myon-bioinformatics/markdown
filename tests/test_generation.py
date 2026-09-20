from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_heading_levels_clamped() -> None:
    assert md.heading("Title") == "# Title\n"
    assert md.heading("Sub", level=2) == "## Sub\n"
    assert md.heading("Deep", level=0) == "# Deep\n"
    assert md.heading("Deep", level=99) == "###### Deep\n"


def test_inline_decorations() -> None:
    assert md.bold("x") == "**x**"
    assert md.italic("x") == "*x*"
    assert md.strikethrough("x") == "~~x~~"


def test_blockquote_multiline() -> None:
    assert md.blockquote("a\nb") == "> a\n> b\n"
    assert md.blockquote("a\n\nb") == "> a\n>\n> b\n"


def test_horizontal_rule() -> None:
    assert md.horizontal_rule() == "---\n"


def test_bullet_and_numbered_list() -> None:
    assert md.bullet_list(["a", "b"]) == "- a\n- b\n"
    assert md.bullet_list([]) == ""
    assert md.numbered_list(["a", "b"]) == "1. a\n2. b\n"


def test_task_item_and_task_list() -> None:
    assert md.task_item("todo") == "- [ ] todo\n"
    assert md.task_item("done", checked=True) == "- [x] done\n"
    assert md.task_list(["a", ("b", True)]) == "- [ ] a\n- [x] b\n"
    assert md.task_list([]) == ""


def test_details_and_footnote_generators() -> None:
    assert md.details("More", "hidden") == ":::details More\nhidden\n:::\n"
    assert md.footnote_ref("1") == "[^1]"
    assert md.footnote("1", "note") == "[^1]: note\n"


def test_inline_code() -> None:
    assert md.inline_code("x = 1") == "`x = 1`"


def test_code_block() -> None:
    assert md.code_block("print(1)", lang="python") == "```python\nprint(1)\n```\n"
    assert md.code_block("plain") == "```\nplain\n```\n"


def test_json_block() -> None:
    out = md.json_block({"a": 1})
    assert out.startswith("```json\n")
    assert out.endswith("```\n")
    assert '"a": 1' in out


def test_status_line() -> None:
    assert md.status_line(True, "all good", "broken") == "✓ all good\n"
    assert md.status_line(False, "all good", "broken") == "⚠ broken\n"


def test_table_basic_and_padding() -> None:
    out = md.table(["a", "b"], [[1, 2], [3]])
    assert out == "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 |  |\n"
    assert md.table([], [["x"]]) == ""


def test_key_value_table() -> None:
    out = md.key_value_table({"mode": "train", "epochs": 10})
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| epochs | 10 |\n"


def test_md_table_header_and_rows() -> None:
    out = md.md_table(["name", "val"], ["loss", "0.01"], ["iou", "0.85"])
    assert out == "| name | val |\n| --- | --- |\n| loss | 0.01 |\n| iou | 0.85 |\n"


def test_md_table_dict_records() -> None:
    out = md.md_table({"name": "loss", "val": "0.01"}, {"name": "iou", "val": "0.85"})
    assert out == "| name | val |\n| --- | --- |\n| loss | 0.01 |\n| iou | 0.85 |\n"


def test_md_table_scalar_fallback_and_empty() -> None:
    assert md.md_table("a", "b") == "| value |\n| --- |\n| a |\n| b |\n"
    assert md.md_table() == ""


def test_md_kv_alternating_and_dict_mixed() -> None:
    out = md.md_kv("mode", "train", "epochs", 10)
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| epochs | 10 |\n"
    out2 = md.md_kv({"mode": "train"}, "device", "cuda")
    assert out2 == "| Key | Value |\n| --- | --- |\n| mode | train |\n| device | cuda |\n"


def test_md_kv_trailing_key_without_value() -> None:
    out = md.md_kv("mode", "train", "orphan")
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| orphan |  |\n"


def test_section_joins_blocks() -> None:
    out = md.section("Summary", [md.bullet_list(["ok"]), md.horizontal_rule()])
    assert out == "## Summary\n" + "- ok\n" + "---\n"
    assert md.section("Top", ["body\n"], level=1) == "# Top\nbody\n"


def test_section_inserts_a_newline_before_a_block_that_would_otherwise_run_on() -> None:
    # A caller-supplied block with no trailing newline of its own (plain
    # prose, unlike every builder above) must not run directly into the
    # next block's leading syntax -- that used to turn a following bullet
    # list's first "- item" into plain text glued onto the prior sentence.
    out = md.section("Report", ["Intro sentence.", md.bullet_list(["one", "two"])])
    assert out == "## Report\nIntro sentence.\n- one\n- two\n"
    html = md.markdown_to_html(out)
    assert "<li>one</li>" in html
    assert "Intro sentence.- one" not in html


def test_wrap_section_markers() -> None:
    out = md.wrap_section("PATHS_TRACE", "body\n")
    assert out == "<!-- BEGIN_SECTION:PATHS_TRACE -->\nbody\n<!-- END_SECTION:PATHS_TRACE -->\n"


def test_generation_functions_exposed_in_all() -> None:
    for name in (
        "heading",
        "bold",
        "italic",
        "strikethrough",
        "blockquote",
        "alert",
        "horizontal_rule",
        "bullet_list",
        "numbered_list",
        "task_item",
        "task_list",
        "details",
        "footnote_ref",
        "footnote",
        "inline_code",
        "code_block",
        "json_block",
        "table",
        "key_value_table",
        "md_table",
        "md_kv",
        "status_line",
        "section",
        "wrap_section",
        "alert_stylesheet",
        "default_stylesheet",
        "ial",
        "with_attributes",
        "markdown_to_kramdown",
        "kramdown_to_markdown",
    ):
        assert name in md.__all__
        assert hasattr(md, name)
