from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures"


def test_https_angle_autolink() -> None:
    html = md.markdown_to_html("See <https://example.com> please\n")
    assert '<a href="https://example.com">https://example.com</a>' in html
    assert "&lt;https://" not in html


def test_http_angle_autolink() -> None:
    html = md.markdown_to_html("See <http://example.com/path>\n")
    assert '<a href="http://example.com/path">http://example.com/path</a>' in html


def test_script_tag_is_not_an_autolink() -> None:
    html = md.markdown_to_html("n <script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "<a " not in html
    assert "&lt;script&gt;" in html


def test_other_angle_tags_stay_escaped() -> None:
    html = md.markdown_to_html("a <b>bold</b> tag\n")
    assert "<b>" not in html
    assert "&lt;b&gt;" in html
    assert "<a " not in html


def test_bare_url_stays_literal() -> None:
    """Bare URLs are still unsupported; only the ``<url>`` form is linked."""
    html = md.markdown_to_html("Visit https://example.com today\n")
    assert "<a " not in html
    assert "https://example.com" in html


def test_markdown_link_still_wins() -> None:
    html = md.markdown_to_html("[docs](https://example.com) and <https://example.com/a>\n")
    assert '<a href="https://example.com">docs</a>' in html
    assert '<a href="https://example.com/a">https://example.com/a</a>' in html


def test_autolink_inside_code_stays_literal() -> None:
    html = md.markdown_to_html("`<https://example.com>`\n")
    assert "<a " not in html
    assert "<code>&lt;https://example.com&gt;</code>" in html


def test_query_ampersand_is_escaped() -> None:
    html = md.markdown_to_html("<https://example.com?a=1&b=2>\n")
    assert '<a href="https://example.com?a=1&amp;b=2">https://example.com?a=1&amp;b=2</a>' in html


def test_unclosed_angle_url_is_escaped_not_linked() -> None:
    html = md.markdown_to_html("see <https://example.com\n")
    assert "<a " not in html
    assert "&lt;https://example.com" in html


def test_angle_autolink_keeps_trailing_underscore_and_parens() -> None:
    """A URL boundary case: ``_`` and ``()`` right after the path are part
    of the URL, not emphasis markers or link-syntax delimiters."""
    html = md.markdown_to_html("<https://a.com/_(test)_>\n")
    assert '<a href="https://a.com/_(test)_">https://a.com/_(test)_</a>' in html
    assert "<em>" not in html


def test_vscode_fixture_live_autolink_renders() -> None:
    content = (FIXTURES / "vscode_readme_snippet.md").read_text(encoding="utf-8")
    html = md.markdown_to_html(content)
    assert '<a href="https://code.visualstudio.com">https://code.visualstudio.com</a>' in html
