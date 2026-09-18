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


def test_code_block() -> None:
    assert md.code_block("print(1)", lang="python") == "```python\nprint(1)\n```\n"
    assert md.code_block("plain") == "```\nplain\n```\n"


def test_table_basic_and_padding() -> None:
    out = md.table(["a", "b"], [[1, 2], [3]])
    assert out == "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 |  |\n"
    assert md.table([], [["x"]]) == ""


def test_key_value_table() -> None:
    out = md.key_value_table({"mode": "train", "epochs": 10})
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| epochs | 10 |\n"


def test_section_joins_blocks() -> None:
    out = md.section("Summary", [md.bullet_list(["ok"]), md.horizontal_rule()])
    assert out == "## Summary\n" + "- ok\n" + "---\n"
    assert md.section("Top", ["body\n"], level=1) == "# Top\nbody\n"


def test_generation_functions_exposed_in_all() -> None:
    for name in (
        "heading",
        "bold",
        "italic",
        "strikethrough",
        "blockquote",
        "horizontal_rule",
        "bullet_list",
        "numbered_list",
        "code_block",
        "table",
        "key_value_table",
        "section",
    ):
        assert name in md.__all__
        assert hasattr(md, name)
