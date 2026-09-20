"""Real, published Markdown documents run through this module end to end.

Unlike the CommonMark spec examples (tiny, isolated constructs), these are
excerpts of actual documents people read every day: GitHub's own Markdown
docs, a real project's CONTRIBUTING.md, and a real project's CHANGELOG.md
(see fixtures/provenance.yaml for exact sources / commits / license).

The goal here (per the benchmark's own brief) is not "make everything
pass" -- it's proving these don't crash, and pinning down exactly which
known-unsupported constructs (bare URL autolinks,
backslash escaping -- see test_benchmark_commonmark.py and
markdown.py's UNSUPPORTED) show up, unmangled, inside a real document
rather than only in an isolated one-liner. GitHub-style alerts, simple
GFM pipe tables, ordinary > blockquotes, ~~strikethrough~~, GFM task
lists, <http(s)://...> autolinks, GFM/Pandoc-like footnotes, and
:::details collapsible sections are now supported subsets (see
test_alerts.py, test_tables.py, test_blockquotes.py,
test_strikethrough.py, test_task_lists.py, test_autolinks.py,
test_footnotes.py, test_details.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures"
BENCHMARK = FIXTURES / "benchmark"


def _provenance() -> dict:
    return yaml.safe_load((FIXTURES / "provenance.yaml").read_text(encoding="utf-8"))


BENCHMARK_FIXTURE_IDS = [f["id"] for f in _provenance()["benchmark_fixtures"] if f["path"].endswith(".md")]


@pytest.mark.parametrize("fixture_id", BENCHMARK_FIXTURE_IDS)
def test_real_document_reads_and_converts_without_raising(fixture_id: str) -> None:
    entry = next(f for f in _provenance()["benchmark_fixtures"] if f["id"] == fixture_id)
    content = (FIXTURES / entry["path"]).read_text(encoding="utf-8")

    inv = md.inventory(content)
    assert inv["heading_count"] >= 1, fixture_id

    html = md.markdown_to_html(content)
    assert html  # non-empty; no exception is the main assertion here

    sections = md.extract_sections(content)
    assert isinstance(sections, list)


def _github_docs_content() -> str:
    return (BENCHMARK / "github_docs_markdown.md").read_text(encoding="utf-8")


def test_github_docs_fixture_has_the_constructs_it_claims() -> None:
    content = _github_docs_content()
    inv = md.inventory(content)
    assert inv["heading_count"] >= 10
    assert inv["link_count"] >= 5
    assert inv["image_count"] >= 5
    assert inv["code_block_count"] >= 5


def test_github_docs_tables_render_as_html_tables() -> None:
    """Matches fixtures/provenance.yaml: the live Style/Syntax table is supported."""
    content = _github_docs_content()
    html = md.markdown_to_html(content)
    assert "<table>" in html
    assert "<th>Style</th>" in html
    assert "First Header" in html


def test_github_docs_live_strikethrough_renders() -> None:
    """The Style/Syntax table's last cell is live ``~~text~~``, not a code span."""
    content = _github_docs_content()
    html = md.markdown_to_html(content)
    assert "<del>This was mistaken text</del>" in html


def test_github_docs_task_list_example_is_inline_code_not_a_live_list() -> None:
    """The excerpt's Task lists section only shows the syntax inside inline code."""
    content = _github_docs_content()
    html = md.markdown_to_html(content)
    assert "<input" not in html
    assert "Optional" in html


def test_github_docs_bare_urls_are_not_autolinked() -> None:
    """Bare URLs in this excerpt stay text; only the ``<url>`` form is linked."""
    content = _github_docs_content()
    html = md.markdown_to_html(content)
    assert "https://github.com/jlord/sheetsee.js/issues/26" in html
    # The table's own [text](url) links still render as <a>.
    assert "<a href=" in html


def test_github_docs_alerts_render_as_asides() -> None:
    content = _github_docs_content()
    html = md.markdown_to_html(content)
    # Real > [!NOTE] blocks in the excerpt become <aside> alerts.
    # The five-kind syntax examples still appear inside a fenced code block.
    assert 'data-alert-flavor="github"' in html
    assert 'class="markdown-alert markdown-alert-note"' in html
    assert "[!WARNING]" in html
    assert "[!CAUTION]" in html


def test_github_docs_fenced_footnote_example_stays_code() -> None:
    """This fixture's footnote syntax lives inside a fenced example, not live."""
    content = _github_docs_content()
    html = md.markdown_to_html(content)
    assert "footnote[^1]" in html
    assert '<section class="footnotes">' not in html


def test_github_docs_nested_fence_example_is_a_single_correctly_closed_block() -> None:
    """The 'Quoting code' section's own quadruple-fence-around-triple-fence example."""
    content = _github_docs_content()
    blocks = md.extract_code_blocks(content)
    nested = next(b for b in blocks if "git status" in b["code"] and "```" in b["code"])
    assert nested["code"].count("```") == 2  # the inner fence's own open+close, preserved verbatim


def test_contributing_escaped_tip_callout_is_not_an_alert() -> None:
    """nodejs CONTRIBUTING.md uses `> \\[!TIP]`, not a GitHub alert opener."""
    content = (BENCHMARK / "contributing_example.md").read_text(encoding="utf-8")
    html = md.markdown_to_html(content)
    assert "markdown-alert" not in html
    assert "[!TIP]" in html
    assert "<blockquote>" in html


def test_contributing_fixture_has_expected_constructs() -> None:
    content = (BENCHMARK / "contributing_example.md").read_text(encoding="utf-8")
    inv = md.inventory(content)
    assert inv["heading_count"] >= 5
    assert inv["link_count"] >= 5
    assert inv["code_block_count"] >= 1


def test_changelog_fixture_is_long_and_stable() -> None:
    """Long-input stability: many headings/links/lists, no exception, no runaway output."""
    content = (BENCHMARK / "changelog_example.md").read_text(encoding="utf-8")
    assert len(content) > 10_000  # genuinely long input, not a token gesture

    inv = md.inventory(content)
    assert inv["heading_count"] >= 20
    assert inv["link_count"] >= 50

    html = md.markdown_to_html(content)
    assert len(html) > len(content) * 0.5  # sanity: output isn't truncated/empty
