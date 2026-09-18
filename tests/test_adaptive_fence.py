"""``code_block()``'s adaptive fence length.

A fixed triple-backtick fence is ambiguous the moment the wrapped content
itself contains a triple-backtick run -- e.g. Markdown source shown as an
example inside a code block, which is exactly what a Markdown-about-Markdown
demo (or this repo's own README) tends to contain. These tests prove the
fence grows exactly enough to stay unambiguous, and that the result actually
round-trips through this module's own reading side (``extract_code_blocks``
/ ``markdown_to_html``) unchanged -- no changes were needed there, since a
fence longer than anything nested inside it was already enough for the
existing ``line.startswith(fence)`` closing scan to find the real close.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_plain_content_keeps_the_original_triple_fence() -> None:
    assert md.code_block("print(1)", lang="python") == "```python\nprint(1)\n```\n"
    assert md.code_block("plain") == "```\nplain\n```\n"


def test_triple_backtick_content_gets_a_quadruple_fence() -> None:
    inner = "```python\nprint('hello')\n```"
    wrapped = md.code_block(inner, lang="markdown")
    assert wrapped == f"````markdown\n{inner}\n````\n"


def test_quadruple_backtick_content_gets_a_quintuple_fence() -> None:
    inner = "````\ninner\n````"
    wrapped = md.code_block(inner)
    assert wrapped == f"`````\n{inner}\n`````\n"


def test_fence_inside_fence_round_trips_through_extract_code_blocks() -> None:
    inner = "```python\nprint('hello')\n```"
    wrapped = md.code_block(inner, lang="markdown")

    blocks = md.extract_code_blocks(wrapped)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "markdown"
    assert blocks[0]["code"] == inner


def test_fence_inside_fence_round_trips_through_markdown_to_html() -> None:
    inner = "```python\nprint('hello')\n```"
    wrapped = md.code_block(inner, lang="markdown")

    html = md.markdown_to_html(wrapped)
    # A single <pre><code> block, not the inner fence's own content escaping out.
    assert html.count("<pre><code") == 1
    assert "print('hello')" in html
    assert "class=\"language-markdown\"" in html


def test_unadaptive_fixed_triple_fence_would_have_broken_the_round_trip() -> None:
    """Document the exact bug adaptive fencing fixes -- a hand-built fixed
    triple fence around the same content mis-parses into two blocks."""
    inner = "```python\nprint('hello')\n```"
    naively_wrapped = f"```markdown\n{inner}\n```\n"

    blocks = md.extract_code_blocks(naively_wrapped)
    assert len(blocks) == 2, "a fixed triple fence closes early on the inner ``` line"


def test_tilde_fence_char() -> None:
    assert md.code_block("plain", fence_char="~") == "~~~\nplain\n~~~\n"


def test_tilde_fence_is_unaffected_by_backticks_in_content() -> None:
    wrapped = md.code_block("has ``` inside", fence_char="~")
    assert wrapped == "~~~\nhas ``` inside\n~~~\n"

    blocks = md.extract_code_blocks(wrapped)
    assert len(blocks) == 1
    assert blocks[0]["code"] == "has ``` inside"


def test_tilde_fence_still_adapts_to_tilde_runs_in_content() -> None:
    inner = "~~~\ncode\n~~~"
    wrapped = md.code_block(inner, fence_char="~")
    assert wrapped == f"~~~~\n{inner}\n~~~~\n"


def test_language_info_string_is_preserved_after_the_fence() -> None:
    wrapped = md.code_block("x = 1", lang="python")
    assert wrapped.splitlines()[0] == "```python"

    nested = md.code_block("```\nx\n```", lang="text")
    assert nested.splitlines()[0] == "````text"


def test_empty_fence_char_raises_instead_of_crashing_the_regex() -> None:
    with pytest.raises(ValueError, match="fence_char"):
        md.code_block("plain", fence_char="")


def test_multi_character_fence_char_raises() -> None:
    """A multi-char fence_char would build a line _FENCE_RE never recognizes as a fence at all."""
    with pytest.raises(ValueError, match="fence_char"):
        md.code_block("plain", fence_char="ab")


def test_non_fence_single_character_raises() -> None:
    with pytest.raises(ValueError, match="fence_char"):
        md.code_block("plain", fence_char="-")
