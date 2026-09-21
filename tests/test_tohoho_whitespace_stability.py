from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

TOHOHO = ROOT / "fixtures" / "benchmark" / "tohoho_web_home.html"


def _first_diff(left: str, right: str) -> tuple[int, str, str]:
    index = next(
        (i for i, (a, b) in enumerate(zip(left, right)) if a != b),
        min(len(left), len(right)),
    )
    lo = max(0, index - 100)
    hi = index + 100
    return index, repr(left[lo:hi]), repr(right[lo:hi])


def test_tohoho_markdown_is_stable_after_html_round_trip() -> None:
    html = TOHOHO.read_text(encoding="utf-8")
    first = md.html_to_markdown(html)
    second = md.html_to_markdown(md.markdown_to_html(first))

    assert first == second, _first_diff(first, second)


def test_tohoho_dom_markdown_is_stable_after_dom_round_trip() -> None:
    html = TOHOHO.read_text(encoding="utf-8")
    first = md.dom_to_markdown(md.parse_html_dom(html))
    second = md.dom_to_markdown(md.markdown_to_dom(first))

    assert first == second, _first_diff(first, second)


def test_html_block_boundaries_drop_formatting_whitespace() -> None:
    html = "prefix   <h2>Heading </h2><ul><li>one </li><li>two</li></ul>"
    markdown = md.html_to_markdown(html)

    assert markdown == "prefix\n\n## Heading\n\n- one\n- two\n"


def test_markdown_hard_break_survives_html_round_trip() -> None:
    source = "first line  \nsecond line\n"

    html = md.markdown_to_html(source)

    assert "<br />" in html
    assert md.html_to_markdown(html) == source


def test_source_text_ending_like_blockquote_prefix_is_still_trimmed() -> None:
    html = "<span>literal &gt; </span><h2>Heading</h2>"

    assert md.html_to_markdown(html) == "literal >\n\n## Heading\n"


def test_nested_list_marker_space_is_preserved_by_parser_provenance() -> None:
    html = "<ul><li><ol><li>nested</li></ol></li></ul>"

    assert md.html_to_markdown(html) == "- \n  1. nested\n"
