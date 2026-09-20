from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_details_exported() -> None:
    assert "details" in md.__all__


def test_details_generator_shape() -> None:
    assert md.details("More") == ":::details More\n:::\n"
    assert md.details("More", "hidden") == ":::details More\nhidden\n:::\n"
    assert md.details("More", "hidden\n") == ":::details More\nhidden\n:::\n"
    assert md.details("") == ":::details\n:::\n"


def test_generator_round_trips_to_details_summary() -> None:
    html = md.markdown_to_html(md.details("More", "hidden body"))
    assert html.startswith("<details>")
    assert "<summary>More</summary>" in html
    assert "<p>hidden body</p>" in html
    assert html.strip().endswith("</details>")


def test_nested_inlines_in_summary_and_body() -> None:
    src = md.details("See **bold** and `code`", "also *em* and [a](https://ex.com)")
    html = md.markdown_to_html(src)
    assert "<summary>See <strong>bold</strong> and <code>code</code></summary>" in html
    assert "<em>em</em>" in html
    assert '<a href="https://ex.com">a</a>' in html


def test_body_blank_lines_split_paragraphs() -> None:
    html = md.markdown_to_html(":::details Title\none\n\ntwo\n:::\n")
    assert html.count("<p>") == 2
    assert "<p>one</p>" in html
    assert "<p>two</p>" in html


def test_summary_and_body_html_is_escaped() -> None:
    html = md.markdown_to_html(
        md.details("<script>x</script>", "<script>alert(1)</script>")
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<details>" in html


def test_raw_html_details_in_markdown_stays_escaped() -> None:
    html = md.markdown_to_html("<details><summary>x</summary>y</details>\n")
    assert "<details>" not in html
    assert "&lt;details&gt;" in html


def test_unclosed_details_consumes_to_eof() -> None:
    html = md.markdown_to_html(":::details Open\nstill hidden\n")
    assert "<details>" in html
    assert "<p>still hidden</p>" in html
    assert "</details>" in html


def test_nested_details_closer_ends_the_outer_block() -> None:
    """Small contract: the first ``:::`` closes; inner :::details is not nested HTML."""
    html = md.markdown_to_html(
        ":::details Outer\n:::details Inner\nhidden\n:::\nafter\n"
    )
    assert html.count("<details>") == 1
    assert ":::details Inner" in html or "Inner" in html
    assert "<p>after</p>" in html


def test_fenced_details_example_stays_code() -> None:
    html = md.markdown_to_html("```\n:::details nope\nhidden\n:::\n```\n")
    assert "<details>" not in html
    assert ":::details nope" in html


def test_details_is_not_an_alert() -> None:
    html = md.markdown_to_html(":::details title\nhidden\n:::\n")
    assert "markdown-alert" not in html
    assert "<details>" in html
