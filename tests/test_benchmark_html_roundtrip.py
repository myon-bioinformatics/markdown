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

The real-world section below fills that gap: fixtures/benchmark/
tohoho_web_home.html is a real, vendored page (see fixtures/provenance.yaml
for its fetched_at/sha256), not synthetic -- checking how far
html_to_markdown() gets on an actual, dense, real site rather than a
hand-picked tag inventory.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures"
BENCHMARK = FIXTURES / "benchmark"

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


# --- Real-world HTML: fixtures/benchmark/tohoho_web_home.html ---
#
# A real, vendored page (not synthetic -- see fixtures/provenance.yaml),
# dense with the constructs the SAMPLE_HTML snippet above never exercises
# at real-world scale: 263 links, 25 headings (1 h1 + 24 h2), semantic
# <header>/<aside>/<main>/<footer> wrappers html_to_markdown() doesn't
# specially handle, a <form>, and inline <script> ad-loading blocks.


def _tohoho_html() -> str:
    return (BENCHMARK / "tohoho_web_home.html").read_text(encoding="utf-8")


def test_tohoho_fixture_has_the_constructs_it_claims() -> None:
    """Matches fixtures/provenance.yaml's own note for this fixture."""
    html = _tohoho_html()
    assert html.count("<h1") == 1
    assert html.count("<h2") == 24
    assert html.count("<a ") == 263


def test_tohoho_headings_and_links_survive_html_to_markdown() -> None:
    """The real benchmark question: does a real, dense page's structure
    survive html_to_markdown() -- not just the hand-picked SAMPLE_HTML
    tags above."""
    markdown_out = md.html_to_markdown(_tohoho_html())
    inv = md.inventory(markdown_out)

    # Every heading and every link makes it through as a real Markdown
    # construct -- no data loss on this fixture's own headings/links.
    assert inv["heading_count"] == 25
    assert inv["link_count"] == 263
    assert inv["image_count"] == 2
    assert "# とほほのWWW入門" in markdown_out
    assert "## メニュー" in markdown_out
    assert "[HOME](index.htm)" in markdown_out


def test_tohoho_semantic_wrapper_tags_degrade_without_losing_their_text() -> None:
    """<header>/<aside>/<main>/<footer> aren't in _HTMLToMarkdownParser's
    handled-tag list (see markdown.py), so they contribute no Markdown
    syntax of their own -- but the real text they wrap must still survive,
    same "unsupported tag, text not data" fallback as everywhere else."""
    markdown_out = md.html_to_markdown(_tohoho_html())
    assert "誤り指摘・要望・コメントなどありましたら" in markdown_out  # inside <div class="my-info">
    assert "Copyright (C) 1996-2026" in markdown_out  # inside <footer><address>


def test_tohoho_scripts_are_suppressed_not_leaked_as_text() -> None:
    """<script> content must never leak into the converted Markdown --
    same suppression _HTMLToMarkdownParser already applies to <style>."""
    markdown_out = md.html_to_markdown(_tohoho_html())
    assert "googletag.cmd.push" not in markdown_out
    assert "FP_BIDDER" not in markdown_out


def test_tohoho_round_trip_keeps_every_heading_and_link() -> None:
    """HTML -> Markdown -> HTML: the real round-trip question, on a real
    page instead of the small synthetic SAMPLE_HTML snippet above."""
    intermediate_markdown = md.html_to_markdown(_tohoho_html())
    final_html = md.markdown_to_html(intermediate_markdown)

    assert final_html.count("<h1>") == 1
    assert final_html.count("<h2>") == 24
    assert final_html.count("<a href=") == 263
    assert "<h1>とほほのWWW入門</h1>" in final_html
    assert '<a href="index.htm">HOME</a>' in final_html
