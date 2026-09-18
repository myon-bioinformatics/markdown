"""Exploratory: HTML -> html_to_markdown() -> markdown_to_html() -> HTML.

This is deliberately kept separate from the PASS/DEGRADED/UNSUPPORTED/FAIL
grading in test_benchmark_commonmark.py and test_benchmark_realworld.py --
round-tripping through two conservative, independent conversions (a
different code path from markdown_to_html() alone) is a different kind of
question ("does structure survive two hops?"), not a parser conformance
score.

The HTML below is a small, synthetic snippet built only from the tags
html_to_markdown() actually handles (see _HTMLToMarkdownParser in
markdown.py: headings, p, br, hr, strong/b, em/i, code, pre, a, img,
ul/ol/li, blockquote) -- not vendored from any specific real page, so it
carries no external provenance the way the other benchmark fixtures do.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

SAMPLE_HTML = """
<h1>Project Title</h1>
<p>A short intro paragraph with <strong>bold</strong> and <em>italic</em> text,
and a <a href="https://example.com">link</a>.</p>
<h2>Features</h2>
<ul>
<li>First feature</li>
<li>Second feature with <code>inline_code()</code></li>
</ul>
<blockquote>A quoted remark.</blockquote>
<pre><code>def hello():
    print("hi")
</code></pre>
<hr>
<p><img src="logo.png" alt="Logo"></p>
""".strip()


def test_html_to_markdown_produces_nonempty_markdown() -> None:
    result = md.html_to_markdown(SAMPLE_HTML)
    assert isinstance(result, str)
    assert result.strip()
    # Spot-check a few conversions landed, without asserting exact formatting.
    assert "# Project Title" in result
    assert "**bold**" in result
    assert "*italic*" in result
    assert "[link](https://example.com)" in result
    assert "- First feature" in result
    assert "```" in result


def test_markdown_from_html_then_back_to_html_round_trips_structure() -> None:
    intermediate_markdown = md.html_to_markdown(SAMPLE_HTML)
    final_html = md.markdown_to_html(intermediate_markdown)

    assert isinstance(final_html, str)
    assert final_html.strip()

    # Exploratory checks, not a fidelity guarantee: the two conversions are
    # independent and conservative, so exact HTML is not expected to match
    # the input byte-for-byte (attribute order, whitespace, self-closing
    # tags, etc. are all allowed to differ).
    assert "<h1>Project Title</h1>" in final_html
    assert "<strong>bold</strong>" in final_html
    assert "<em>italic</em>" in final_html
    assert '<a href="https://example.com">link</a>' in final_html
    assert "<li>First feature" in final_html and "</li>" in final_html
    assert "<pre><code>" in final_html


def test_round_trip_does_not_crash_on_the_repos_own_readme() -> None:
    """A softer sanity check with a real (if self-referential) document."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    html = md.markdown_to_html(readme)
    back_to_markdown = md.html_to_markdown(html)
    assert isinstance(back_to_markdown, str)
    # No crash and no data loss is the bar here -- not exact text equality.
    assert back_to_markdown.strip()
