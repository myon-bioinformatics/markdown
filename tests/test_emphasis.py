from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_plain_bold_and_italic() -> None:
    html = md.markdown_to_html("plain **bold** and *italic* text\n")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_triple_asterisk_is_bold_wrapped_in_italic() -> None:
    html = md.markdown_to_html("***triple***\n")
    assert "<em><strong>triple</strong></em>" in html


def test_strong_nested_inside_em_when_em_is_the_outer_pair() -> None:
    """Single-``*`` outer delimiters around a ``**bold**`` inner pair works:
    the ``**`` regex runs first and removes its asterisks, so the outer
    single ``*`` pair is left clean to match afterwards."""
    html = md.markdown_to_html("*italic **bold** italic*\n")
    assert "<em>italic <strong>bold</strong> italic</em>" in html


def test_em_nested_inside_strong_is_a_documented_degrade() -> None:
    """The opposite nesting order is UNSUPPORTED: the ``**`` (strong) regex
    requires content with no ``*`` at all, so a ``*em*`` pair inside a
    ``**...**`` pair breaks the outer match and both delimiter runs stay
    literal text -- only the inner ``*em*`` renders.

    See UNSUPPORTED["parser"]: "nested emphasis edge cases (asymmetric
    delimiter runs ...)".
    """
    html = md.markdown_to_html("**bold *italic* bold**\n")
    assert "<strong>" not in html
    assert "<em>italic</em>" in html
    assert "**bold" in html
    assert "bold**" in html


def test_asymmetric_close_run_is_also_a_documented_degrade() -> None:
    html = md.markdown_to_html("**bold *italic***\n")
    assert "<strong>" not in html
    assert "<em>" not in html
    assert "**bold *italic***" in html
