from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_plain_blockquote() -> None:
    html = md.markdown_to_html(md.blockquote("quoted"))
    assert html == "<blockquote>\n<p>quoted</p>\n</blockquote>\n"
    assert "markdown-alert" not in html


def test_multiline_blockquote_joins_like_paragraphs() -> None:
    html = md.markdown_to_html("> quoted\n> lines\n")
    assert html.startswith("<blockquote>")
    assert "<p>quoted lines</p>" in html
    assert html.endswith("</blockquote>\n")


def test_blank_gt_lines_split_paragraphs() -> None:
    html = md.markdown_to_html(md.blockquote("a\n\nb"))
    assert html == "<blockquote>\n<p>a</p>\n<p>b</p>\n</blockquote>\n"


def test_inline_formatting_inside_blockquote() -> None:
    html = md.markdown_to_html("> hello **world** and `code`\n")
    assert "<strong>world</strong>" in html
    assert "<code>code</code>" in html
    assert "<blockquote>" in html


def test_blockquote_html_is_escaped() -> None:
    html = md.markdown_to_html("> <script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_quote_adjacent_to_alert_keeps_both() -> None:
    content = "> ordinary quote\n\n> [!NOTE]\n> Useful info\n"
    html = md.markdown_to_html(content)
    assert "<blockquote>" in html
    assert "<p>ordinary quote</p>" in html
    assert "<aside " in html
    assert 'data-alert-flavor="github"' in html
    assert "Useful info" in html


def test_quote_then_alert_without_blank_line_still_splits() -> None:
    """Alerts win when the opener is ``[!TYPE]``, even with no blank line."""
    content = "> ordinary quote\n> [!NOTE]\n> Useful info\n"
    html = md.markdown_to_html(content)
    assert "<blockquote>" in html
    assert "<p>ordinary quote</p>" in html
    assert "<aside " in html
    assert 'data-alert="NOTE"' in html
    assert "[!NOTE]" not in html


def test_alert_still_renders_as_aside_not_blockquote() -> None:
    html = md.markdown_to_html(md.alert("NOTE", "Useful **info**"))
    assert "<aside " in html
    assert "<blockquote>" not in html
    assert "<strong>info</strong>" in html


def test_inner_heading_stays_paragraph_text() -> None:
    """Nested block constructs inside a quote are not re-parsed (small contract)."""
    html = md.markdown_to_html("> # Foo\n> bar\n")
    assert "<blockquote>" in html
    assert "<h1>" not in html
    assert "# Foo" in html


def test_paragraph_then_blockquote_interrupts() -> None:
    html = md.markdown_to_html("before\n> quoted\nafter\n")
    assert html.startswith("<p>before</p>")
    assert "<blockquote>" in html
    assert html.endswith("<p>after</p>\n")


def test_blockquote_round_trip_single_paragraph() -> None:
    source = "> quoted\n"
    html = md.markdown_to_html(source)
    assert md.html_to_markdown(html) == source
    assert md.dom_to_markdown(md.markdown_to_dom(source)) == source


def test_blockquote_round_trip_multiple_paragraphs() -> None:
    source = "> a\n>\n> b\n"
    html = md.markdown_to_html(source)
    assert md.html_to_markdown(html) == source
    assert md.dom_to_markdown(md.markdown_to_dom(source)) == source


def test_blockquote_round_trip_inline_formatting() -> None:
    source = "> hello **world** and `code`\n"
    html = md.markdown_to_html(source)
    assert md.html_to_markdown(html) == source
    assert md.dom_to_markdown(md.markdown_to_dom(source)) == source
