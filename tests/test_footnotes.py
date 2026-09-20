from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_footnote_helpers_exported() -> None:
    assert "footnote" in md.__all__
    assert "footnote_ref" in md.__all__


def test_footnote_generators() -> None:
    assert md.footnote_ref("1") == "[^1]"
    assert md.footnote("1", "the note") == "[^1]: the note\n"


def test_generator_round_trips_to_superscript_and_section() -> None:
    src = f"See {md.footnote_ref('1')}.\n\n{md.footnote('1', 'the note')}"
    html = md.markdown_to_html(src)
    assert '<sup class="footnote-ref">' in html
    assert 'href="#fn-1"' in html
    assert 'id="fnref-1"' in html
    assert ">1</a>" in html
    assert '<section class="footnotes">' in html
    assert '<li id="fn-1">the note' in html
    assert 'href="#fnref-1"' in html
    assert "footnote-backref" in html


def test_named_id_and_inline_formatting_in_note() -> None:
    src = "Go [^note].\n\n[^note]: see **bold** and `code`\n"
    html = md.markdown_to_html(src)
    assert 'id="fn-note"' in html
    assert 'id="fnref-note"' in html
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html


def test_undefined_ref_stays_literal() -> None:
    html = md.markdown_to_html("missing [^nope] here\n")
    assert "<sup" not in html
    assert "footnotes" not in html
    assert "[^nope]" in html


def test_duplicate_ids_first_definition_wins() -> None:
    html = md.markdown_to_html("x [^1]\n\n[^1]: first\n\n[^1]: second\n")
    assert "first" in html
    assert "second" not in html


def test_unused_definition_is_dropped() -> None:
    html = md.markdown_to_html("plain\n\n[^1]: unused\n")
    assert "unused" not in html
    assert "footnotes" not in html
    assert "<p>plain</p>" in html


def test_indented_continuation_is_kept() -> None:
    html = md.markdown_to_html("n [^1]\n\n[^1]: first\n    second\n")
    assert "first second" in html
    assert "<li id=" in html


def test_unindented_wrapping_is_not_continuation() -> None:
    html = md.markdown_to_html("n [^1]\n\n[^1]: first\nsecond\n")
    assert "first" in html
    assert "<p>second</p>" in html


def test_note_html_is_escaped() -> None:
    html = md.markdown_to_html("x [^1]\n\n[^1]: <script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "footnotes" in html


def test_code_span_and_fence_are_not_footnotes() -> None:
    html = md.markdown_to_html("`[^1]`\n\n```\n[^1]: nope\n```\n")
    assert "<sup" not in html
    assert "<code>[^1]</code>" in html
    assert "[^1]: nope" in html


def test_first_reference_order_numbers_labels() -> None:
    html = md.markdown_to_html("b [^b] a [^a]\n\n[^a]: A\n\n[^b]: B\n")
    assert ">1</a></sup>" in html
    assert ">2</a></sup>" in html
    # First referenced id (b) is footnote 1.
    assert 'href="#fn-b"' in html
    assert html.index('href="#fn-b"') < html.index('href="#fn-a"')


def test_repeat_ref_shares_number_and_only_first_gets_id() -> None:
    html = md.markdown_to_html("a [^1] b [^1]\n\n[^1]: note\n")
    assert html.count(">1</a>") == 2
    assert html.count('id="fnref-1"') == 1
    assert html.count('href="#fn-1"') >= 2


def test_fenced_github_docs_style_example_stays_code() -> None:
    html = md.markdown_to_html(
        "```text\nHere is a simple footnote[^1].\n\n[^1]: My reference.\n```\n"
    )
    assert "<sup" not in html
    assert "footnote[^1]" in html
    assert "footnotes" not in html
