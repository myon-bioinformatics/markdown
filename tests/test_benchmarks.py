"""📊 Benchmarks and real-world documents: CommonMark, the HTML round trip, the optimization guard, published Markdown and the real-world pages report."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


# ═══ · benchmark commonmark ══════════════════════════════════════════════════════════════════════════════
# CommonMark spec examples as a stress test -- not a compliance claim.
#
# Loads fixtures/benchmark/commonmark_examples.yaml (13 of the official
# CommonMark spec's own numbered examples) and asserts markdown_to_html()'s
# *current* output for each matches the recorded ``our_html`` baseline. This
# module isn't a full CommonMark engine (see markdown.py's own SUPPORTED /
# UNSUPPORTED), so several of these are expected, recorded FAILs -- that's
# the point: this is a regression pin on "what we know doesn't work today",
# not an aspiration that everything here passes.
#
# If markdown.py's parsing genuinely changes (a real fix, not an accident),
# update the matching ``our_html`` / ``classification`` in the YAML deliberately
# -- a diff there is a design decision, not something to silence.

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

BENCHMARK_COMMONMARK_FIXTURES = ROOT / "fixtures" / "benchmark"
VALID_CLASSIFICATIONS = {"PASS", "DEGRADED", "UNSUPPORTED", "FAIL"}


def _load_examples() -> list[dict]:
    data = yaml.safe_load((BENCHMARK_COMMONMARK_FIXTURES / "commonmark_examples.yaml").read_text(encoding="utf-8"))
    return data["examples"]


EXAMPLES = _load_examples()


def test_commonmark_examples_file_is_well_formed() -> None:
    assert len(EXAMPLES) >= 10
    seen_ids = set()
    for ex in EXAMPLES:
        assert ex["classification"] in VALID_CLASSIFICATIONS, ex["id"]
        assert ex["id"] not in seen_ids, f"duplicate id: {ex['id']}"
        seen_ids.add(ex["id"])
        assert isinstance(ex["spec_example"], int)
        assert ex["markdown"]
        assert ex["commonmark_html"]
        assert ex["our_html"]


@pytest.mark.parametrize("example", EXAMPLES, ids=[ex["id"] for ex in EXAMPLES])
def test_recorded_output_matches_current_behavior(example: dict) -> None:
    """Regression pin: today's markdown_to_html() output must match what was recorded."""
    actual = md.markdown_to_html(example["markdown"]).rstrip("\n")
    assert actual == example["our_html"], (
        f"{example['id']} (spec example {example['spec_example']}): "
        f"behavior changed -- update commonmark_examples.yaml deliberately if this is a real fix"
    )


@pytest.mark.parametrize(
    "example",
    [ex for ex in EXAMPLES if ex["classification"] == "PASS"],
    ids=[ex["id"] for ex in EXAMPLES if ex["classification"] == "PASS"],
)
def test_pass_classified_examples_actually_match_commonmark(example: dict) -> None:
    """Anything marked PASS must genuinely match the spec's own expected HTML."""
    actual = md.markdown_to_html(example["markdown"]).rstrip("\n")
    assert actual == example["commonmark_html"], example["id"]


def test_at_least_one_example_per_requested_category() -> None:
    requested = {
        "headings",
        "emphasis",
        "nested_emphasis",
        "escaping",
        "blockquote",
        "nested_list",
        "fenced_code",
        "inline_code",
        "horizontal_rule",
        "links",
        "edge_cases",
    }
    covered = {ex["category"] for ex in EXAMPLES}
    missing = requested - covered
    assert not missing, f"no CommonMark example for: {missing}"


def test_classification_summary_is_printable() -> None:
    """Not a real assertion -- keeps the human-readable summary from ``pytest -s`` handy."""
    counts: dict[str, int] = {}
    for ex in EXAMPLES:
        counts[ex["classification"]] = counts.get(ex["classification"], 0) + 1
    lines = [f"  {k}: {v}" for k, v in sorted(counts.items())]
    summary = "CommonMark benchmark classification counts:\n" + "\n".join(lines)
    print("\n" + summary)
    assert sum(counts.values()) == len(EXAMPLES)


# ═══ · benchmark html roundtrip ══════════════════════════════════════════════════════════════════════════
# Exploratory: HTML -> html_to_markdown() -> markdown_to_html() -> HTML.
#
# This is deliberately kept separate from the PASS/DEGRADED/UNSUPPORTED/FAIL
# grading in test_benchmark_commonmark.py and test_benchmark_realworld.py --
# round-tripping through two conservative, independent conversions (a
# different code path from markdown_to_html() alone) is a different kind of
# question ("does structure survive two hops?"), not a parser conformance
# score.
#
# The HTML below is a small, synthetic snippet built only from the tags
# html_to_markdown() actually handles (see _HTMLToMarkdownParser in
# markdown.py: headings, p, br, hr, strong/b, em/i, del, code, pre, a, img,
# ul/ol/li, blockquote, table/thead/th/td, checkbox inputs) -- not vendored
# from any specific real page, so it carries no external provenance the way
# the other benchmark fixtures do.
#
# The real-world section below fills that gap: fixtures/benchmark/
# tohoho_web_home.html is a real, vendored page (see fixtures/provenance.yaml
# for its fetched_at/sha256), not synthetic -- checking how far
# html_to_markdown() gets on an actual, dense, real site rather than a
# hand-picked tag inventory.

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
    assert "<blockquote>" in final_html
    assert "quoted remark" in final_html.lower()


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


# ═══ · benchmark optimization guard ══════════════════════════════════════════════════════════════════════
# Fault-injection checks do not require a historical git checkout.

class BenchmarkGuardTests(unittest.TestCase):
    def test_scanner_and_toc_mismatches_stop_optimized_execution(self):
        for attribute, replacement, diagnostic in (
            ('_scan_lines', 'lambda lines: []', 'scanner field mismatch'),
            ('table_of_contents', 'lambda content: object()', 'table of contents mismatch'),
        ):
            code = f'''
import runpy, sys, types, markdown
reference = types.ModuleType('guard_reference')
reference._scan_lines = markdown._scan_lines
reference.table_of_contents = markdown.table_of_contents
sys.modules['guard_reference'] = reference
ns = runpy.run_path('scripts/benchmark_scanned_lines.py')['main'].__globals__
ns['subprocess'].check_output = lambda *a, **kw: b'from guard_reference import _scan_lines, table_of_contents'
markdown.{attribute} = {replacement}
ns['main']()
'''
            with self.subTest(attribute=attribute):
                result = subprocess.run([sys.executable, '-O', '-S', '-c', code],
                                        cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(diagnostic, result.stderr)
                self.assertEqual(result.stdout, '')


# ═══ · benchmark realworld ═══════════════════════════════════════════════════════════════════════════════
# Real, published Markdown documents run through this module end to end.
#
# Unlike the CommonMark spec examples (tiny, isolated constructs), these are
# excerpts of actual documents people read every day: GitHub's own Markdown
# docs, a real project's CONTRIBUTING.md, and a real project's CHANGELOG.md
# (see fixtures/provenance.yaml for exact sources / commits / license).
#
# The goal here (per the benchmark's own brief) is not "make everything
# pass" -- it's proving these don't crash, and pinning down exactly which
# known-unsupported constructs (bare URL autolinks,
# backslash escaping -- see test_benchmark_commonmark.py and
# markdown.py's UNSUPPORTED) show up, unmangled, inside a real document
# rather than only in an isolated one-liner. GitHub-style alerts, simple
# GFM pipe tables, ordinary > blockquotes, ~~strikethrough~~, GFM task
# lists, <http(s)://...> autolinks, GFM/Pandoc-like footnotes, and
# :::details collapsible sections are now supported subsets (see
# test_alerts.py, test_tables.py, test_blockquotes.py,
# test_strikethrough.py, test_task_lists.py, test_autolinks.py,
# test_footnotes.py, test_details.py).

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def test_github_docs_structural_generators_scale_to_real_document() -> None:
    """Recent one-way structural generators should handle a real docs excerpt."""
    content = _github_docs_content()
    mindmap = md.markdown_headings_to_mermaid_mindmap(content, root="GitHub Docs")
    dot = md.markdown_links_to_dot(content)

    assert mindmap.startswith("mindmap\n")
    # Structural generators deliberately ignore fenced/inline examples, while
    # inventory() answers a broader lexical question. Pin real live headings
    # instead of comparing unlike counters.
    assert mindmap.count('["') >= 10
    assert '["Headings"]' in mindmap
    assert '["Alerts"]' in mindmap

    assert dot.startswith("digraph markdown_links {\n")
    # Same rule for links: prove real link-graph scale/content without treating
    # fenced/inline-code links as live graph edges.
    assert dot.count(" -> ") >= 5
    assert "https://docs.github.com" in dot or "https://github.com" in dot


def test_changelog_structural_generators_are_deterministic_on_long_input() -> None:
    """Long real-world input stays deterministic for the new graph generators."""
    content = (BENCHMARK / "changelog_example.md").read_text(encoding="utf-8")

    first_mindmap = md.markdown_headings_to_mermaid_mindmap(content)
    second_mindmap = md.markdown_headings_to_mermaid_mindmap(content)
    first_dot = md.markdown_links_to_dot(content)
    second_dot = md.markdown_links_to_dot(content)

    assert first_mindmap == second_mindmap
    assert first_dot == second_dot
    assert len(first_mindmap) > 500
    assert len(first_dot) > 1000


# ═══ · real world pages report ═══════════════════════════════════════════════════════════════════════════
# Smoke tests for scripts/real_world_pages_report.py.
#
# The GitHub Pages workflow runs:
#
#     python scripts/real_world_pages_report.py --out _site
#
# ``_site`` is relative. ``Path.as_uri()`` raises ValueError on a relative
# path, which is what broke run 35455946035 after PR #14. These tests pin
# that the report resolves before taking a file URI, without requiring
# Playwright or its browsers (screenshots are already best-effort).
#
# Revision identity is injected as a dict so unit tests do not need a real
# git checkout or GitHub Actions env (same idea as flutter_navigation_basic
# overriding BuildMetadata.load in widget tests).

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_FAKE_REVISION = {
    "version": "0.1.0",
    "sha": "abcdef1234567890abcdef1234567890abcdef12",
    "shortSha": "abcdef12",
    "ref": "main",
    "committedAt": "2026-09-19T16:50:27Z",
    "subject": "Fix GitHub Pages report crash",
    "commitUrl": "https://github.com/myon-bioinformatics/markdown/commit/abcdef1234567890abcdef1234567890abcdef12",
    "dirty": False,
}


def _load_report_module():
    path = ROOT / "scripts" / "real_world_pages_report.py"
    spec = importlib.util.spec_from_file_location("real_world_pages_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_screenshot(report, monkeypatch) -> list[str]:
    seen_uris: list[str] = []

    def fake_screenshot(file_uri: str, png_path: Path) -> bool:
        seen_uris.append(file_uri)
        parsed = urlparse(file_uri)
        assert parsed.scheme == "file", file_uri
        local = Path(unquote(parsed.path))
        assert local.is_absolute(), file_uri
        return False

    monkeypatch.setattr(report, "_screenshot", fake_screenshot)
    return seen_uris


def test_build_report_with_relative_out_does_not_raise_on_as_uri(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)
    seen_uris = _stub_screenshot(report, monkeypatch)

    report.build_report(Path("_site"))

    assert (tmp_path / "_site" / "index.html").is_file()
    assert seen_uris
    assert all(uri.startswith("file://") for uri in seen_uris)


def test_pages_favicon_is_local_and_benchmark_outputs_remain_unbranded(tmp_path, monkeypatch):
    report = _load_report_module()
    _stub_screenshot(report, monkeypatch)
    site = tmp_path / "nested" / "_site"
    report.build_report(site, revision=_FAKE_REVISION)

    index = (site / "index.html").read_text(encoding="utf-8")
    assert '<link rel="icon" type="image/png" href="./favicon.png">' in index
    assert '<link rel="apple-touch-icon" href="./icon.png">' in index
    assert 'src="./icon.png"' in index
    assert (site / "icon.png").read_bytes() == (ROOT / "docs/brand/icon.png").read_bytes()
    source = (ROOT / "docs/brand/favicon.png").read_bytes()
    assert source.startswith(b"\x89PNG\r\n\x1a\n")
    assert (site / "favicon.png").read_bytes() == source
    for entry in report._load_html_fixtures():
        original = (ROOT / "fixtures" / entry["path"]).read_text(encoding="utf-8")
        assert (site / entry["id"] / "original.html").read_text(encoding="utf-8") == original
        roundtrip = (site / entry["id"] / "roundtrip.html").read_text(encoding="utf-8")
        expected_body = report.md.markdown_to_html(report.md.html_to_markdown(original))
        assert roundtrip == f"<!doctype html><html><body>{expected_body}</body></html>\n"
    (site / "favicon.png").write_bytes(b"old icon")
    report.build_report(site, revision=_FAKE_REVISION)
    assert (site / "favicon.png").read_bytes() == source


def test_build_report_embeds_injected_revision_and_writes_build_meta(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)
    seen_uris = _stub_screenshot(report, monkeypatch)

    report.build_report(Path("_site"), revision=_FAKE_REVISION)

    index = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert "abcdef12" in index
    assert "Version 0.1.0" in index
    assert 'id="build-meta"' in index
    assert _FAKE_REVISION["commitUrl"] in index
    assert _FAKE_REVISION["committedAt"] in index
    assert _FAKE_REVISION["subject"] in index
    assert _FAKE_REVISION["sha"] in index
    assert seen_uris
    assert all(uri.startswith("file://") for uri in seen_uris)

    meta_path = tmp_path / "_site" / "build_meta.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["shortSha"] == "abcdef12"
    assert meta["sha"] == _FAKE_REVISION["sha"]
    assert meta["commitUrl"] == _FAKE_REVISION["commitUrl"]
    assert meta["version"] == "0.1.0"


def test_build_report_omits_version_label_when_absent(tmp_path, monkeypatch) -> None:
    report = _load_report_module()
    monkeypatch.chdir(tmp_path)
    _stub_screenshot(report, monkeypatch)

    revision = {**_FAKE_REVISION, "version": None}
    report.build_report(Path("_site"), revision=revision)

    index = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    assert "abcdef12" in index
    assert "Version " not in index
    assert "Commit abcdef12" in index


@pytest.mark.parametrize('case', json.loads(
    (ROOT / 'tests/fixtures/pages_revision_migration.json').read_text()
), ids=lambda case: case['name'])
def test_revision_before_after_fixture(case, monkeypatch):
    report = _load_report_module()
    expected = case['after']

    def canonical(root, *, repository, env):
        assert root == report.ROOT
        assert repository == 'myon-bioinformatics/markdown'
        assert env == case['env']
        if case['name'] == 'unavailable':
            raise FileNotFoundError('git')
        return {'head': {'sha': expected['sha'], 'branch': expected['ref'],
                         'timestamp': expected['committedAt'], 'subject': expected['subject']}}

    def status(root):
        assert root == report.ROOT
        if case['name'] == 'unavailable':
            raise report.GH_IDENTITY.GitInspectionError('git unavailable')
        return {'clean': not expected['dirty'], 'truncated': False}

    monkeypatch.setattr(report.GH_IDENTITY, 'repository_metadata_v1', canonical)
    monkeypatch.setattr(report.GH_IDENTITY, 'git_status', status)
    assert report.collect_revision(case['env']) == expected
    assert set(case['before']) == set(expected)
    if case['name'] in ('clean', 'dirty'):
        assert case['before'] == expected
    rendered = report._revision_html(expected)
    if expected['dirty'] is None:
        assert '(dirty unknown)' in rendered
    elif expected['dirty']:
        assert '(dirty)' in rendered
    else:
        assert '(dirty' not in rendered


def _checkout(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-b', 'main')
    git('config', 'user.name', 'Pages fixture')
    git('config', 'user.email', 'pages@example.invalid')
    (tmp_path / 'tracked.txt').write_text('initial\n')
    git('add', 'tracked.txt')
    git('commit', '-m', 'Pages fixture commit')
    return git


def test_real_checkout_clean_dirty_detached_and_actions(tmp_path, monkeypatch):
    report = _load_report_module()
    git = _checkout(tmp_path)
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    sha = git('rev-parse', 'HEAD')
    clean = report.collect_revision({})
    assert clean['sha'] == sha
    assert clean['shortSha'] == sha[:8]
    assert clean['ref'] == 'main'
    assert clean['subject'] == 'Pages fixture commit'
    assert clean['committedAt'] == git('show', '-s', '--format=%cI', 'HEAD')
    assert clean['dirty'] is False
    # Existing inspector handles filenames, including Unicode and newlines.
    untracked = tmp_path / '未追跡\nfile.txt'
    untracked.write_text('untracked')
    assert report.collect_revision({})['dirty'] is True
    untracked.unlink()
    (tmp_path / 'tracked.txt').write_text('modified\n')
    assert report.collect_revision({})['dirty'] is True
    git('add', 'tracked.txt')
    assert report.collect_revision({})['dirty'] is True
    git('commit', '-m', 'Updated fixture')
    git('checkout', '--detach')
    detached = report.collect_revision({})
    assert detached['ref'] == 'detached'
    assert detached['dirty'] is False
    actions = report.collect_revision({'GITHUB_SHA': 'f'*40,
                                      'GITHUB_REF_NAME': '42/merge',
                                      'GITHUB_HEAD_REF': 'feature/pages'})
    assert actions['sha'] == detached['sha']
    assert actions['ref'] == 'feature/pages'
    assert report.collect_revision({'GITHUB_REF_NAME': '42/merge'})['ref'] == '42/merge'


@pytest.mark.parametrize('failure', ['missing_git', 'not_worktree', 'unborn'])
def test_unmeasurable_checkout(tmp_path, monkeypatch, failure):
    report = _load_report_module()
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    if failure == 'missing_git':
        monkeypatch.setenv('PATH', str(tmp_path))
    elif failure == 'unborn':
        subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    meta = report.collect_revision({'GITHUB_SHA': 'a'*40, 'GITHUB_REF_NAME': 'main'})
    assert all(meta[key] is None for key in
               ('sha', 'shortSha', 'ref', 'committedAt', 'subject', 'commitUrl'))
    # An unborn worktree can have a successfully measured clean status despite
    # its identity being unknown; the two measurements remain independent.
    assert meta['dirty'] is (False if failure == 'unborn' else None)


@pytest.mark.parametrize('failure', ['error', 'truncated'])
def test_status_failure_does_not_erase_identity(tmp_path, monkeypatch, failure):
    report = _load_report_module()
    git = _checkout(tmp_path)
    monkeypatch.setattr(report, 'ROOT', tmp_path)

    def status(root):
        if failure == 'error':
            raise report.GH_IDENTITY.GitInspectionError('failed observation')
        return {'clean': False, 'truncated': True, 'records': []}

    monkeypatch.setattr(report.GH_IDENTITY, 'git_status', status)
    meta = report.collect_revision({})
    assert meta['sha'] == git('rev-parse', 'HEAD')
    assert meta['dirty'] is None
    assert '(dirty unknown)' in report._revision_html(meta)


@pytest.mark.parametrize("failure", ["validation", "git"] )
def test_canonical_validation_failure_keeps_dirty_observation(tmp_path, monkeypatch, failure):
    report = _load_report_module()
    _checkout(tmp_path)
    monkeypatch.setattr(report, 'ROOT', tmp_path)
    (tmp_path / 'tracked.txt').write_text('modified')

    def fail(*args, **kwargs):
        if failure == 'git':
            raise report.GH_IDENTITY.GitInspectionError('git unavailable')
        raise ValueError('canonical metadata is not valid')

    monkeypatch.setattr(report.GH_IDENTITY, 'repository_metadata_v1', fail)
    monkeypatch.setattr(report.md, '__version__', '9.9.9', raising=False)
    meta = report.collect_revision({'GITHUB_SHA': 'a'*40})
    assert meta['sha'] is None
    assert meta['dirty'] is True
    assert meta['version'] == '9.9.9'
