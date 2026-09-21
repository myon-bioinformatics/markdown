from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_markdown_nested_unordered_list_preserves_structure() -> None:
    source = "- foo\n  - bar\n    - baz\n"
    html = md.markdown_to_html(source)

    assert html == (
        "<ul>\n"
        "<li>foo\n"
        "<ul>\n"
        "<li>bar\n"
        "<ul>\n"
        "<li>baz</li>\n"
        "</ul>\n"
        "</li>\n"
        "</ul>\n"
        "</li>\n"
        "</ul>\n"
    )
    assert md.html_to_markdown(html) == source


def test_markdown_mixed_ul_ol_round_trip() -> None:
    source = "- one\n- two\n  1. nested\n- tail\n"
    html = md.markdown_to_html(source)

    assert "<ul>" in html
    assert "<ol>" in html
    assert "<li>two\n<ol>" in html
    assert md.html_to_markdown(html) == source
    assert md.dom_to_markdown(md.markdown_to_dom(source)) == source


def test_html_mixed_list_round_trip_stays_stable() -> None:
    html = "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>"
    markdown = md.html_to_markdown(html)

    assert markdown == "- one\n- \n  1. nested\n"
    assert md.html_to_markdown(md.markdown_to_html(markdown)) == markdown
    assert md.dom_to_markdown(md.parse_html_dom(html)) == markdown


def test_nested_list_keeps_inline_formatting() -> None:
    source = "- outer **bold**\n  1. inner `code`\n"
    html = md.markdown_to_html(source)

    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert md.html_to_markdown(html) == source


def test_ordered_parent_with_unordered_child_round_trip() -> None:
    source = "1. parent\n   - child\n2. tail\n"
    html = md.markdown_to_html(source)

    assert "<ol>" in html
    assert "<ul>" in html
    assert "<li>parent\n<ul>" in html
    assert md.html_to_markdown(html) == source


def test_nested_task_items_use_same_list_nesting_engine() -> None:
    source = "- parent\n  - [ ] todo\n  - [x] done\n"
    html = md.markdown_to_html(source)

    assert html.count('type="checkbox"') == 2
    assert '<input type="checkbox" disabled /> todo' in html
    assert '<input type="checkbox" disabled checked /> done' in html
    assert md.html_to_markdown(html) == source


def test_tab_indented_child_list_is_nested() -> None:
    source = "- parent\n\t1. child\n"
    html = md.markdown_to_html(source)

    assert "<li>parent\n<ol>" in html
    # Canonical Markdown emitted by HTML conversion uses two spaces per depth.
    assert md.html_to_markdown(html) == "- parent\n  1. child\n"


def test_list_kind_switches_at_same_indent_start_new_sibling_list() -> None:
    source = "- bullet\n1. numbered\n"
    html = md.markdown_to_html(source)

    assert html == "<ul>\n<li>bullet</li>\n</ul>\n<ol>\n<li>numbered</li>\n</ol>\n"
