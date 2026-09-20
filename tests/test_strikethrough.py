from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_generator_round_trips_to_del() -> None:
    html = md.markdown_to_html(md.strikethrough("x"))
    assert html == "<p><del>x</del></p>\n"
    assert "<s>" not in html


def test_phrase_round_trip() -> None:
    src = md.strikethrough("This was mistaken text")
    html = md.markdown_to_html(src)
    assert "<del>This was mistaken text</del>" in html


def test_nested_with_bold_and_italic() -> None:
    inner = md.markdown_to_html("~~**bold**~~")
    assert "<del><strong>bold</strong></del>" in inner

    outer = md.markdown_to_html("**~~strike~~**")
    assert "<strong><del>strike</del></strong>" in outer

    italic = md.markdown_to_html("~~*em*~~")
    assert "<del><em>em</em></del>" in italic


def test_unmatched_tilde_pair_stays_literal() -> None:
    """A lone ``~~`` is not strikethrough (documented degrade)."""
    html = md.markdown_to_html("keep ~~ this")
    assert "<del>" not in html
    assert "~~" in html


def test_first_pair_wins_on_odd_run() -> None:
    html = md.markdown_to_html("~~a~~b~~")
    assert "<del>a</del>b~~" in html


def test_single_tilde_inside_pair_is_kept() -> None:
    html = md.markdown_to_html("~~a~b~~")
    assert "<del>a~b</del>" in html


def test_escaped_html_inside_strikethrough() -> None:
    html = md.markdown_to_html("~~<script>alert(1)</script>~~")
    assert "<script>" not in html
    assert "<del>&lt;script&gt;alert(1)&lt;/script&gt;</del>" in html


def test_code_span_is_not_strikethrough() -> None:
    html = md.markdown_to_html("`~~code~~`")
    assert "<del>" not in html
    assert "<code>~~code~~</code>" in html


def test_fenced_example_stays_code() -> None:
    html = md.markdown_to_html("```\n~~nope~~\n```\n")
    assert "<del>" not in html
    assert "~~nope~~" in html
