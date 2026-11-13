"""📝 Markdown syntax and generation: fences, alerts, links, quotes, details, emphasis, footnotes, lists, tables, task lists, TOC, dialects, kramdown, diagrams, trees, stylesheets and the line scanner."""
from __future__ import annotations

import copy
import pickle
import re
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
import markdown as md


# ═══ · adaptive fence ════════════════════════════════════════════════════════════════════════════════════
# ``code_block()``'s adaptive fence length.
#
# A fixed triple-backtick fence is ambiguous the moment the wrapped content
# itself contains a triple-backtick run -- e.g. Markdown source shown as an
# example inside a code block, which is exactly what a Markdown-about-Markdown
# demo (or this repo's own README) tends to contain. These tests prove the
# fence grows exactly enough to stay unambiguous, and that the result actually
# round-trips through this module's own reading side (``extract_code_blocks``
# / ``markdown_to_html``) unchanged -- no changes were needed there, since a
# fence longer than anything nested inside it was already enough for the
# existing ``line.startswith(fence)`` closing scan to find the real close.

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


# ═══ · alerts ════════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


BENCHMARK = ROOT / "fixtures" / "benchmark"


def test_alert_exported() -> None:
    assert "alert" in md.__all__
    assert "ALERT_FLAVORS" in md.__all__
    assert "GITHUB_ALERT_KINDS" in md.__all__
    assert md.ALERT_FLAVORS == ("github", "qiita", "zenn", "obsidian", "gitlab")


def test_github_alert_generator_uppercase_and_multiline() -> None:
    assert md.alert("note", "Useful information that users should know") == (
        "> [!NOTE]\n> Useful information that users should know\n"
    )
    assert md.alert("warning", "a\nb") == "> [!WARNING]\n> a\n> b\n"
    assert md.alert("TIP", "a\n\nb") == "> [!TIP]\n> a\n>\n> b\n"
    assert md.alert("caution", "") == "> [!CAUTION]\n"


def test_github_alert_unknown_kind_and_title_fail_loud() -> None:
    with pytest.raises(ValueError, match="unknown GitHub alert kind"):
        md.alert("danger", "nope")
    with pytest.raises(ValueError, match="same-line title"):
        md.alert("note", "x", title="Heads up")
    with pytest.raises(ValueError, match="fold"):
        md.alert("note", "x", fold="-")
    with pytest.raises(ValueError, match="unknown alert flavor"):
        md.alert("note", "x", flavor="notion")


def test_qiita_note_generator() -> None:
    assert md.alert("info", "インフォメーション", flavor="qiita") == (
        ":::note info\nインフォメーション\n:::\n"
    )
    assert md.alert("note", "省略形", flavor="qiita") == ":::note info\n省略形\n:::\n"
    assert md.alert("warn", "注意\n二行", flavor="qiita") == (
        ":::note warn\n注意\n二行\n:::\n"
    )
    assert md.alert("ALERT", "強い警告", flavor="qiita") == (
        ":::note alert\n強い警告\n:::\n"
    )
    with pytest.raises(ValueError, match="unknown Qiita note kind"):
        md.alert("tip", "x", flavor="qiita")


def test_zenn_message_generator() -> None:
    assert md.alert("message", "メッセージをここに", flavor="zenn") == (
        ":::message\nメッセージをここに\n:::\n"
    )
    assert md.alert("info", "info synonym", flavor="zenn") == (
        ":::message\ninfo synonym\n:::\n"
    )
    assert md.alert("alert", "警告メッセージをここに", flavor="zenn") == (
        ":::message alert\n警告メッセージをここに\n:::\n"
    )
    with pytest.raises(ValueError, match="unknown Zenn message kind"):
        md.alert("warn", "x", flavor="zenn")


def test_obsidian_callout_generator_title_and_fold() -> None:
    assert md.alert("warning", "Check config", flavor="obsidian") == (
        "> [!warning]\n> Check config\n"
    )
    assert md.alert(
        "note",
        "body",
        flavor="obsidian",
        title="Custom title",
    ) == "> [!note] Custom title\n> body\n"
    assert md.alert(
        "faq",
        "Yes",
        flavor="obsidian",
        fold="-",
        title="Foldable?",
    ) == "> [!faq]- Foldable?\n> Yes\n"
    with pytest.raises(ValueError, match="invalid Obsidian callout type"):
        md.alert("not a type", "x", flavor="obsidian")


def test_gitlab_alert_generator_lowercase_optional_title() -> None:
    assert md.alert("WARNING", "dangerous", flavor="gitlab") == (
        "> [!warning]\n> dangerous\n"
    )
    assert md.alert(
        "note",
        "unrecoverable",
        flavor="gitlab",
        title="Data deletion",
    ) == "> [!note] Data deletion\n> unrecoverable\n"
    with pytest.raises(ValueError, match="unknown GitLab alert kind"):
        md.alert("bug", "x", flavor="gitlab")


def test_markdown_to_html_github_alert() -> None:
    html = md.markdown_to_html(md.alert("NOTE", "Useful **info**"))
    assert 'data-alert-flavor="github"' in html
    assert 'data-alert="NOTE"' in html
    assert 'class="markdown-alert markdown-alert-note"' in html
    assert '<p class="markdown-alert-title">NOTE</p>' in html
    assert "<strong>info</strong>" in html
    assert "<aside " in html
    assert "[!NOTE]" not in html


def test_markdown_to_html_qiita_and_zenn() -> None:
    qiita = md.markdown_to_html(md.alert("warn", "注意してください", flavor="qiita"))
    assert 'data-alert-flavor="qiita"' in qiita
    assert 'data-alert="WARN"' in qiita
    assert "注意してください" in qiita
    assert ":::" not in qiita

    zenn_info = md.markdown_to_html(md.alert("message", "メッセージをここに", flavor="zenn"))
    assert 'data-alert-flavor="zenn"' in zenn_info
    assert 'data-alert="MESSAGE"' in zenn_info

    zenn_alert = md.markdown_to_html(md.alert("alert", "警告", flavor="zenn"))
    assert 'data-alert="ALERT"' in zenn_alert
    assert 'markdown-alert-alert' in zenn_alert


def test_qiita_note_without_info_kind_parses() -> None:
    html = md.markdown_to_html(":::note\ninfoは省略可能です。\n:::\n")
    assert 'data-alert-flavor="qiita"' in html
    assert 'data-alert="INFO"' in html
    assert "infoは省略可能です。" in html


def test_obsidian_title_fold_and_custom_type() -> None:
    titled = md.markdown_to_html(
        "> [!warning] Data deletion\n> The following would be dangerous.\n"
    )
    assert 'data-alert-flavor="obsidian"' in titled
    assert 'data-alert="WARNING"' in titled
    assert "Data deletion" in titled
    assert "dangerous" in titled

    folded = md.markdown_to_html("> [!faq]- Are callouts foldable?\n> Yes!\n")
    assert 'data-alert-flavor="obsidian"' in folded
    assert 'data-alert-fold="closed"' in folded
    assert "Are callouts foldable?" in folded

    custom = md.markdown_to_html("> [!custom-question-type]\n> hi\n")
    assert 'data-alert-flavor="obsidian"' in custom
    assert 'data-alert="CUSTOM-QUESTION-TYPE"' in custom


def test_github_uppercase_not_confused_with_obsidian_title() -> None:
    github = md.markdown_to_html("> [!TIP]\n> Helpful advice\n")
    assert 'data-alert-flavor="github"' in github
    obsidian = md.markdown_to_html("> [!tip]\n> Helpful advice\n")
    assert 'data-alert-flavor="obsidian"' in obsidian


def test_gitlab_generated_lowercase_parses_as_obsidian() -> None:
    html = md.markdown_to_html(md.alert("note", "useful", flavor="gitlab"))
    assert 'data-alert-flavor="obsidian"' in html
    assert 'data-alert="NOTE"' in html


def test_multiline_alert_body_and_adjacent_paragraphs() -> None:
    content = (
        "Before the note.\n"
        "\n"
        "> [!NOTE]\n"
        "> line one\n"
        "> line two\n"
        "\n"
        "After the note.\n"
    )
    html = md.markdown_to_html(content)
    assert html.startswith("<p>Before the note.</p>")
    assert html.endswith("<p>After the note.</p>\n")
    assert 'data-alert-flavor="github"' in html
    assert "line one" in html
    assert "line two" in html


def test_ordinary_blockquote_renders() -> None:
    html = md.markdown_to_html("> quoted\n> lines\n")
    assert html == "<blockquote>\n<p>quoted lines</p>\n</blockquote>\n"
    assert "markdown-alert" not in html


def test_alert_body_html_is_escaped() -> None:
    html = md.markdown_to_html(md.alert("NOTE", "<script>alert(1)</script>"))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_unknown_qiita_and_zenn_openers_are_not_alerts() -> None:
    qiita = md.markdown_to_html(":::note spicy\nnope\n:::\n")
    assert "markdown-alert" not in qiita
    assert ":::note spicy" in qiita or "note spicy" in qiita

    zenn = md.markdown_to_html(":::message warn\nnope\n:::\n")
    assert "markdown-alert" not in zenn

    details = md.markdown_to_html(":::details title\nhidden\n:::\n")
    assert "markdown-alert" not in details
    assert "<details>" in details
    assert "<summary>title</summary>" in details


def test_fenced_github_alert_examples_stay_code() -> None:
    content = (
        "```markdown\n"
        "> [!WARNING]\n"
        "> Urgent info\n"
        "```\n"
    )
    html = md.markdown_to_html(content)
    assert "<aside" not in html
    assert "[!WARNING]" in html
    assert "<pre><code" in html


def test_gitlab_multiline_triple_gt_is_unsupported() -> None:
    html = md.markdown_to_html(">>> [!note] Things to consider\nbody\n>>>\n")
    assert "markdown-alert" not in html
    assert "<aside" not in html
    # Leading > lines parse as an ordinary quote; leftover > stays escaped
    # paragraph text so this cannot collapse into an Obsidian alert.
    assert "<blockquote>" in html
    assert "[!note]" in html


def test_github_docs_fixture_real_alerts_render() -> None:
    content = (BENCHMARK / "github_docs_markdown.md").read_text(encoding="utf-8")
    html = md.markdown_to_html(content)
    assert html.count('data-alert-flavor="github"') >= 5
    assert 'data-alert="NOTE"' in html
    # The five-kind syntax examples remain inside a fenced code block.
    assert "[!WARNING]" in html
    assert "[!CAUTION]" in html


# ═══ · autolinks ═════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


# ═══ · blockquotes ═══════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def test_blockquote_round_trip_preserves_paragraph_attributes() -> None:
    html = '<blockquote><p id="q" class="note">quoted</p></blockquote>'
    markdown = md.html_to_markdown(html)

    assert markdown == "> quoted {#q .note}\n"
    assert md.dom_to_markdown(md.parse_html_dom(html)) == markdown


# ═══ · details ═══════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_details_exported() -> None:
    assert "details" in md.__all__


def test_details_generator_shape() -> None:
    assert md.details("More") == ":::details More\n:::\n"
    assert md.details("More", "hidden") == ":::details More\nhidden\n:::\n"
    assert md.details("More", "hidden\n") == ":::details More\nhidden\n:::\n"
    assert md.details("") == ":::details\n:::\n"


def test_generator_round_trips_to_details_summary() -> None:
    html = md.markdown_to_html(md.details("More", "hidden body"))
    assert html.startswith("<details>")
    assert "<summary>More</summary>" in html
    assert "<p>hidden body</p>" in html
    assert html.strip().endswith("</details>")


def test_nested_inlines_in_summary_and_body() -> None:
    src = md.details("See **bold** and `code`", "also *em* and [a](https://ex.com)")
    html = md.markdown_to_html(src)
    assert "<summary>See <strong>bold</strong> and <code>code</code></summary>" in html
    assert "<em>em</em>" in html
    assert '<a href="https://ex.com">a</a>' in html


def test_body_blank_lines_split_paragraphs() -> None:
    html = md.markdown_to_html(":::details Title\none\n\ntwo\n:::\n")
    assert html.count("<p>") == 2
    assert "<p>one</p>" in html
    assert "<p>two</p>" in html


def test_summary_and_body_html_is_escaped() -> None:
    html = md.markdown_to_html(
        md.details("<script>x</script>", "<script>alert(1)</script>")
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<details>" in html


def test_raw_html_details_in_markdown_stays_escaped() -> None:
    html = md.markdown_to_html("<details><summary>x</summary>y</details>\n")
    assert "<details>" not in html
    assert "&lt;details&gt;" in html


def test_unclosed_details_consumes_to_eof() -> None:
    html = md.markdown_to_html(":::details Open\nstill hidden\n")
    assert "<details>" in html
    assert "<p>still hidden</p>" in html
    assert "</details>" in html


def test_nested_details_closer_ends_the_outer_block() -> None:
    """Small contract: the first ``:::`` closes; inner :::details is not nested HTML."""
    html = md.markdown_to_html(
        ":::details Outer\n:::details Inner\nhidden\n:::\nafter\n"
    )
    assert html.count("<details>") == 1
    assert ":::details Inner" in html or "Inner" in html
    assert "<p>after</p>" in html


def test_fenced_details_example_stays_code() -> None:
    html = md.markdown_to_html("```\n:::details nope\nhidden\n:::\n```\n")
    assert "<details>" not in html
    assert ":::details nope" in html


def test_details_is_not_an_alert() -> None:
    html = md.markdown_to_html(":::details title\nhidden\n:::\n")
    assert "markdown-alert" not in html
    assert "<details>" in html


def test_details_code_preserves_language_and_container_marker():
    source = ':::details Code\nbefore\n```python\n:::\n<script>\n\n\n```\nafter\n:::\noutside\n'
    result = md.markdown_to_html(source)
    assert '<pre><code class="language-python">:::\n&lt;script&gt;\n\n\n</code></pre>' in result
    assert '<p>after</p>\n</details>\n<p>outside</p>' in result


def test_details_multiple_tilde_and_backtick_code_blocks():
    result = md.markdown_to_html(':::details Code\n~~~text\na\n~~~\nmiddle\n```\nb\n```\n:::\n')
    assert result.count('<pre><code') == 2
    assert '<p>middle</p>' in result
    assert 'a\n</code></pre>' in result
    assert 'b\n</code></pre>' in result


def test_unclosed_code_fence_keeps_colon_closer_as_code_until_eof():
    result = md.markdown_to_html(':::details Code\n```\na\n:::\n')
    assert '<pre><code>a\n:::\n</code></pre>\n</details>' in result


# ═══ · emphasis ══════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


# ═══ · footnotes ═════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


# ═══ · nested lists ══════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_markdown_nested_unordered_list_preserves_structure() -> None:
    source = "- foo\n  - bar\n    - baz\n"
    html = md.markdown_to_html(source)

    assert html == (
        "<ul>\n"
        "<li>foo\n"
        "<ul>\n"
        "<li>bar\n"
        "<ul>\n"
        "<li>baz</li>\n"
        "</ul>\n"
        "</li>\n"
        "</ul>\n"
        "</li>\n"
        "</ul>\n"
    )
    assert md.html_to_markdown(html) == source


def test_markdown_mixed_ul_ol_round_trip() -> None:
    source = "- one\n- two\n  1. nested\n- tail\n"
    html = md.markdown_to_html(source)

    assert "<ul>" in html
    assert "<ol>" in html
    assert "<li>two\n<ol>" in html
    assert md.html_to_markdown(html) == source
    assert md.dom_to_markdown(md.markdown_to_dom(source)) == source


def test_html_mixed_list_round_trip_stays_stable() -> None:
    html = "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>"
    markdown = md.html_to_markdown(html)

    assert markdown == "- one\n- \n  1. nested\n"
    assert md.html_to_markdown(md.markdown_to_html(markdown)) == markdown
    assert md.dom_to_markdown(md.parse_html_dom(html)) == markdown


def test_nested_list_keeps_inline_formatting() -> None:
    source = "- outer **bold**\n  1. inner `code`\n"
    html = md.markdown_to_html(source)

    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert md.html_to_markdown(html) == source


def test_ordered_parent_with_unordered_child_round_trip() -> None:
    source = "1. parent\n   - child\n2. tail\n"
    html = md.markdown_to_html(source)

    assert "<ol>" in html
    assert "<ul>" in html
    assert "<li>parent\n<ul>" in html
    # HTML -> Markdown canonicalizes nesting to two spaces per depth.
    assert md.html_to_markdown(html) == "1. parent\n  - child\n2. tail\n"


def test_nested_task_items_use_same_list_nesting_engine() -> None:
    source = "- parent\n  - [ ] todo\n  - [x] done\n"
    html = md.markdown_to_html(source)

    assert html.count('type="checkbox"') == 2
    assert '<input type="checkbox" disabled /> todo' in html
    assert '<input type="checkbox" disabled checked /> done' in html
    assert md.html_to_markdown(html) == source


def test_tab_indented_child_list_is_nested() -> None:
    source = "- parent\n\t1. child\n"
    html = md.markdown_to_html(source)

    assert "<li>parent\n<ol>" in html
    # Canonical Markdown emitted by HTML conversion uses two spaces per depth.
    assert md.html_to_markdown(html) == "- parent\n  1. child\n"


def test_list_kind_switches_at_same_indent_start_new_sibling_list() -> None:
    source = "- bullet\n1. numbered\n"
    html = md.markdown_to_html(source)

    assert html == "<ul>\n<li>bullet</li>\n</ul>\n<ol>\n<li>numbered</li>\n</ol>\n"


# ═══ · strikethrough ═════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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


def test_html_del_becomes_strikethrough_markdown() -> None:
    md_out = md.html_to_markdown("<p>drop <del>this</del> bit</p>")
    assert "~~this~~" in md_out
    html = md.markdown_to_html(md_out)
    assert "<del>this</del>" in html


# ═══ · tables ════════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_table_generator_round_trips_to_html() -> None:
    src = md.table(["a", "b"], [[1, 2], [3, 4]])
    html = md.markdown_to_html(src)
    assert "<table>" in html
    assert "<thead>" in html
    assert "<th>a</th>" in html
    assert "<th>b</th>" in html
    assert "<tbody>" in html
    assert "<td>1</td>" in html
    assert "<td>2</td>" in html
    assert "<td>3</td>" in html
    assert "<td>4</td>" in html


def test_key_value_table_and_md_table_round_trip() -> None:
    kv = md.markdown_to_html(md.key_value_table({"mode": "train", "epochs": 10}))
    assert "<th>Key</th>" in kv
    assert "<td>mode</td>" in kv
    assert "<td>train</td>" in kv

    built = md.markdown_to_html(md.md_table(["name", "val"], ["loss", "0.01"]))
    assert "<th>name</th>" in built
    assert "<td>loss</td>" in built
    assert "<td>0.01</td>" in built


def test_short_row_is_padded_like_the_generator() -> None:
    src = md.table(["a", "b"], [[1]])
    html = md.markdown_to_html(src)
    assert html.count("<th>") == 2
    # One data row, two cells (the missing one is an empty <td></td>).
    assert "<tr><td>1</td><td></td></tr>" in html


def test_header_only_table_still_emits_thead_and_tbody() -> None:
    html = md.markdown_to_html("| a | b |\n| --- | --- |\n")
    assert "<table>" in html
    assert "<thead>" in html
    assert "<th>a</th>" in html
    assert "<tbody>" in html
    assert "<td>" not in html


def test_inline_formatting_inside_cells() -> None:
    src = "| x | y |\n| --- | --- |\n| **b** | `c` |\n"
    html = md.markdown_to_html(src)
    assert "<strong>b</strong>" in html
    assert "<code>c</code>" in html


def test_escaped_pipe_in_markdown_source_stays_one_cell() -> None:
    """A ``\\|`` in the Markdown source (not just html_to_markdown output)
    stays inside its cell instead of splitting it, mirroring what
    ``table()`` itself generates for a value containing ``|``."""
    html = md.markdown_to_html("| a | b |\n| --- | --- |\n| x\\|y | z |\n")
    assert html.count("<tr>") == 2
    assert "<td>x|y</td>" in html
    assert "<td>z</td>" in html


def test_cell_html_is_escaped() -> None:
    html = md.markdown_to_html("| x |\n| --- |\n| <script>alert(1)</script> |\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_malformed_table_without_separator_stays_paragraph() -> None:
    """A pipe row with no ``| --- |`` delimiter is not a table.

    Documented degrade: the line is escaped/flattened as a paragraph, the
    same fallback as before tables were supported. No ``<table>`` is invented.
    """
    html = md.markdown_to_html("| a | b |\n| 1 | 2 |\n")
    assert "<table" not in html
    assert "<p>" in html
    assert "a" in html
    assert "b" in html


def test_separator_without_header_is_not_a_table() -> None:
    html = md.markdown_to_html("| --- | --- |\n| 1 | 2 |\n")
    assert "<table" not in html


def test_hyphen_run_shorter_than_three_is_not_a_delimiter() -> None:
    html = md.markdown_to_html("| a | b |\n| - | - |\n| 1 | 2 |\n")
    assert "<table" not in html


def test_alignment_colons_are_accepted_but_not_emitted() -> None:
    html = md.markdown_to_html(
        "| Left | Center | Right |\n"
        "| :--- | :---: | ---: |\n"
        "| a | b | c |\n"
    )
    assert "<table>" in html
    assert "<th>Left</th>" in html
    assert "align=" not in html


def test_optional_outer_pipes_and_paragraph_interrupt() -> None:
    html = md.markdown_to_html("before\na | b\n--- | ---\n1 | 2\nafter\n")
    assert html.startswith("<p>before</p>")
    assert html.endswith("<p>after</p>\n")
    assert "<th>a</th>" in html
    assert "<td>1</td>" in html


def test_list_item_with_pipes_is_not_a_table_header() -> None:
    html = md.markdown_to_html("- a | b\n| --- | --- |\n")
    assert "<table" not in html
    assert "<li>" in html


def test_fenced_table_example_stays_code() -> None:
    content = "```markdown\n| a | b |\n| --- | --- |\n| 1 | 2 |\n```\n"
    html = md.markdown_to_html(content)
    assert "<table" not in html
    assert "<pre><code" in html
    assert "| a | b |" in html


def test_github_docs_live_table_renders() -> None:
    content = (BENCHMARK / "github_docs_markdown.md").read_text(encoding="utf-8")
    html = md.markdown_to_html(content)
    assert "<table>" in html
    assert "<th>Style</th>" in html
    assert "<th>Syntax</th>" in html
    # Live strikethrough in the last cell of that table.
    assert "<del>This was mistaken text</del>" in html
    # The "Creating a table" fenced example stays code, not a second live table
    # of "First Header" as <th>.
    assert "First Header" in html
    assert "<th>First Header" not in html


def test_html_table_with_thead_becomes_gfm_pipes() -> None:
    html = (
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    )
    md_out = md.html_to_markdown(html)
    assert "| a | b |" in md_out
    assert "| --- | --- |" in md_out
    assert "| 1 | 2 |" in md_out


def test_markdown_table_round_trips_through_html_to_markdown() -> None:
    src = md.table(["a", "b"], [[1, 2], [3, 4]])
    back = md.html_to_markdown(md.markdown_to_html(src))
    assert "| a | b |" in back
    assert "| 1 | 2 |" in back
    assert "| 3 | 4 |" in back
    html = md.markdown_to_html(back)
    assert "<th>a</th>" in html
    assert "<td>3</td>" in html


def test_th_row_without_thead_is_still_a_header() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>x</th><th>y</th></tr><tr><td>1</td><td>2</td></tr></table>"
    )
    assert md_out.splitlines()[0] == "| x | y |"
    assert "| 1 | 2 |" in md_out


def test_headerless_table_uses_empty_header_so_rows_stay_data() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><td>a</td><td>b</td></tr><tr><td>1</td><td>2</td></tr></table>"
    )
    lines = [line for line in md_out.splitlines() if line.startswith("|")]
    assert lines[0] == "|  |  |"
    assert lines[1] == "| --- | --- |"
    assert "| a | b |" in md_out
    assert "| 1 | 2 |" in md_out


def test_pipe_in_cell_is_escaped() -> None:
    md_out = md.html_to_markdown(
        "<table><thead><tr><th>a</th></tr></thead>"
        "<tbody><tr><td>x|y</td></tr></tbody></table>"
    )
    assert r"| x\|y |" in md_out
    html = md.markdown_to_html(md_out)
    assert "<td>x|y</td>" in html


def test_inline_markup_inside_cells_survives() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>h</th></tr><tr><td><strong>b</strong> and <em>i</em></td></tr></table>"
    )
    assert "| **b** and *i* |" in md_out


def test_nested_table_flattens_into_the_cell() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>h</th></tr>"
        "<tr><td>outer<table><tr><td>inner</td></tr></table></td></tr></table>"
    )
    assert md_out.count("| --- |") == 1
    assert "inner" in md_out
    assert "outer" in md_out


def test_colspan_is_ignored_as_a_single_cell() -> None:
    md_out = md.html_to_markdown(
        '<table><tr><th>a</th><th>b</th></tr>'
        '<tr><td colspan="2">wide</td></tr></table>'
    )
    assert "| wide |" in md_out or "| wide |  |" in md_out


def test_table_section_tags_preserve_row_order() -> None:
    html = (
        "<table>"
        "<thead><tr><th>h</th></tr></thead>"
        "<tbody><tr><td>body</td></tr></tbody>"
        "<tfoot><tr><td>foot</td></tr></tfoot>"
        "</table>"
    )
    md_out = md.html_to_markdown(html)
    lines = [line for line in md_out.splitlines() if line.startswith("|")]

    assert lines[0] == "| h |"
    assert "| body |" in md_out
    assert "| foot |" in md_out
    assert lines.index("| body |") < lines.index("| foot |")


def test_pretty_printed_tr_whitespace_does_not_create_cells() -> None:
    html = """
<table>
  <thead>
    <tr>
      <th>a</th>
      <th>b</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>2</td>
    </tr>
  </tbody>
</table>
"""
    md_out = md.html_to_markdown(html)

    assert md_out == "| a | b |\n| --- | --- |\n| 1 | 2 |\n"


def test_mixed_th_td_row_keeps_cell_order() -> None:
    md_out = md.html_to_markdown(
        "<table><tr><th>kind</th><td>value</td></tr>"
        "<tr><td>x</td><td>1</td></tr></table>"
    )

    assert md_out.splitlines()[0] == "| kind | value |"
    assert "| x | 1 |" in md_out


# ═══ · task lists ════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_task_item_generator() -> None:
    assert md.task_item("todo") == "- [ ] todo\n"
    assert md.task_item("done", checked=True) == "- [x] done\n"
    assert md.task_item() == "- [ ]\n"
    assert md.task_item(checked=True) == "- [x]\n"


def test_task_list_generator() -> None:
    assert md.task_list(["a", ("b", True)]) == "- [ ] a\n- [x] b\n"
    assert md.task_list([]) == ""


def test_generator_round_trips_to_disabled_checkboxes() -> None:
    html = md.markdown_to_html(md.task_list(["todo", ("done", True)]))
    assert html.startswith("<ul>")
    assert html.endswith("</ul>\n")
    assert '<input type="checkbox" disabled /> todo' in html
    assert '<input type="checkbox" disabled checked /> done' in html
    # Not interactive: no name/id, and disabled is always present.
    assert html.count("disabled") == 2
    assert "onclick" not in html
    assert "<input" in html


def test_checked_is_case_insensitive() -> None:
    html = md.markdown_to_html("- [x] lower\n- [X] upper\n")
    assert html.count("checked") == 2
    assert "<li>" in html


def test_star_and_plus_markers_are_tasks() -> None:
    star = md.markdown_to_html("* [ ] star\n")
    plus = md.markdown_to_html("+ [x] plus\n")
    assert '<input type="checkbox" disabled /> star' in star
    assert '<input type="checkbox" disabled checked /> plus' in plus


def test_mixed_task_and_ordinary_items_stay_one_list() -> None:
    """Smaller contract: mixed ``<li>`` shapes in one ``<ul>``, not split lists."""
    html = md.markdown_to_html("- [ ] task\n- ordinary\n- [x] done\n")
    assert html.count("<ul>") == 1
    assert html.count("</ul>") == 1
    assert '<input type="checkbox" disabled /> task' in html
    assert "<li>ordinary</li>" in html
    assert '<input type="checkbox" disabled checked /> done' in html


def test_adjacent_ordinary_list_without_blank_line_is_still_one_ul() -> None:
    html = md.markdown_to_html("- alpha\n- [ ] beta\n")
    assert html.count("<ul>") == 1
    assert "<li>alpha</li>" in html
    assert "beta" in html


def test_blank_line_starts_a_new_list() -> None:
    html = md.markdown_to_html("- alpha\n\n- [ ] beta\n")
    assert html.count("<ul>") == 2


def test_numbered_checkbox_syntax_is_not_a_task() -> None:
    html = md.markdown_to_html("1. [ ] not a task\n")
    assert "<ol>" in html
    assert "<input" not in html
    assert "[ ] not a task" in html


def test_missing_space_after_bracket_is_not_a_task() -> None:
    html = md.markdown_to_html("- [x]done\n")
    assert "<input" not in html
    assert "[x]done" in html


def test_inline_formatting_inside_task_text() -> None:
    html = md.markdown_to_html("- [ ] see **bold** and `code`\n")
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert "<input" in html


def test_task_html_is_escaped() -> None:
    html = md.markdown_to_html("- [ ] <script>alert(1)</script>\n")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<input" in html


def test_fenced_task_example_stays_code() -> None:
    html = md.markdown_to_html("```\n- [ ] nope\n```\n")
    assert "<input" not in html
    assert "- [ ] nope" in html


def test_html_checkbox_li_becomes_task_markdown() -> None:
    md_out = md.html_to_markdown(
        "<ul>"
        '<li><input type="checkbox" disabled /> todo</li>'
        '<li><input type="checkbox" disabled checked /> done</li>'
        "</ul>"
    )
    assert "- [ ] todo" in md_out
    assert "- [x] done" in md_out
    html = md.markdown_to_html(md_out)
    assert '<input type="checkbox" disabled /> todo' in html
    assert '<input type="checkbox" disabled checked /> done' in html


# ═══ · table of contents ═════════════════════════════════════════════════════════════════════════════════
# Tests for slugify and table_of_contents functions in markdown.py.

def test_slugify_basic():
    assert md.slugify("Hello World!") == "hello-world"
    assert md.slugify("User & Permissions (v2.0)") == "user--permissions-v20"
    assert md.slugify("  Spaces   And\tTabs  ") == "spaces---andtabs"


def test_slugify_formatting_and_links():
    assert md.slugify("Heading with `code` and **bold**") == "heading-with-code-and-bold"
    assert md.slugify("Click [here](https://example.com) for details") == "click-here-for-details"


def test_slugify_unicode():
    assert md.slugify("日本語の見出し 1.0") == "日本語の見出し-10"


def test_table_of_contents_basic():
    content = """# Title
## Section 1
### Subsection 1.1
## Section 2
"""
    toc = md.table_of_contents(content)
    assert toc == (
        "- [Title](#title)\n"
        "  - [Section 1](#section-1)\n"
        "    - [Subsection 1.1](#subsection-11)\n"
        "  - [Section 2](#section-2)\n"
    )


def test_table_of_contents_level_filtering():
    content = """# H1
## H2
### H3
#### H4
"""
    toc = md.table_of_contents(content, min_level=2, max_level=3)
    assert toc == (
        "- [H2](#h2)\n"
        "  - [H3](#h3)\n"
    )


def test_table_of_contents_duplicate_slugs():
    content = """# Overview
## Overview
### Overview
"""
    toc = md.table_of_contents(content)
    assert toc == (
        "- [Overview](#overview)\n"
        "  - [Overview](#overview-1)\n"
        "    - [Overview](#overview-2)\n"
    )


def test_table_of_contents_fenced_code_ignored():
    content = """# Real Heading

```markdown
# Ignored Code Heading
```

## Another Real Heading
"""
    toc = md.table_of_contents(content)
    assert toc == (
        "- [Real Heading](#real-heading)\n"
        "  - [Another Real Heading](#another-real-heading)\n"
    )


def test_table_of_contents_invalid_level_bounds():
    with pytest.raises(ValueError):
        md.table_of_contents("# Test", min_level=0)
    with pytest.raises(ValueError):
        md.table_of_contents("# Test", max_level=7)
    with pytest.raises(ValueError):
        md.table_of_contents("# Test", min_level=3, max_level=2)


def test_table_of_contents_no_headings():
    assert md.table_of_contents("Just prose without headings.") == ""


@pytest.mark.parametrize("source, kwargs, expected", [
    ("# Repeat\n## Repeat", {"min_level": 2}, "- [Repeat](#repeat-1)\n"),
    ("### Repeat\n## Repeat", {"max_level": 2}, "- [Repeat](#repeat-1)\n"),
    ("# A\n# A\n# A-1", {}, "- [A](#a)\n- [A](#a-1)\n- [A-1](#a-1-1)\n"),
    ("# A-1\n# A\n# A", {}, "- [A-1](#a-1)\n- [A](#a)\n- [A](#a-2)\n"),
    ("# `code`", {}, "- [code](#code)\n"),
    ("# `code` and **bold**", {}, "- [code and bold](#code-and-bold)\n"),
    ("# [API](https://example.com)", {}, "- [API](#api)\n"),
    ("   # Indented ###", {}, "- [Indented](#indented)\n"),
    ("#\n## ###", {}, "- [](#)\n  - [](#-1)\n"),
    ("    # Code\n# Real", {}, "- [Real](#real)\n"),
    ("<!--\n# Hidden\n-->\n# Visible", {}, "- [Visible](#visible)\n"),
    ("<!--\n```\n-->\n# Visible", {}, "- [Visible](#visible)\n"),
    ("~~~\n# Hidden\n~~~\n# Visible", {}, "- [Visible](#visible)\n"),
])
def test_table_of_contents_regressions(source, kwargs, expected):
    assert md.table_of_contents(source, **kwargs) == expected


@pytest.mark.parametrize("heading, expected", [
    ("foo_bar", "foo_bar"),
    ("Hello  World", "hello--world"),
    ("Cafe\u0301", "cafe\u0301"),
    ("Hello\tWorld", "helloworld"),
    ("_Italic_ and **bold**", "italic-and-bold"),
    ("日本語 😀", "日本語-"),
])
def test_slugify_github_style_subset(heading, expected):
    assert md.slugify(heading) == expected


@pytest.mark.parametrize("value", [True, False, 1.5, "2", None])
@pytest.mark.parametrize("argument", ["min_level", "max_level"])
def test_table_of_contents_non_integer_bounds(value, argument):
    with pytest.raises(ValueError):
        md.table_of_contents("# Heading", **{argument: value})


def test_table_of_contents_labels_are_plain_escaped_text():
    assert md.table_of_contents("# `a[b]` & `*x*`") == (
        "- [a\\[b\\] &amp; \\*x\\*](#ab--x)\n"
    )


@pytest.mark.parametrize("source, expected", [
    ("# Heading <!-- hidden -->", "- [Heading](#heading)\n"),
    ("# A <!-- hidden --> B", "- [A  B](#a--b)\n"),
    ("# A <!-- hidden\n# Hidden\n-->\n# B", "- [A](#a)\n- [B](#b)\n"),
    ("# `<!-- sample -->`", "- [&lt;!-- sample --&gt;](#---sample---)\n"),
])
def test_table_of_contents_inline_comments(source, expected):
    assert md.table_of_contents(source) == expected


# ═══ · dialects ══════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CANONICAL = """# Title

Intro with **bold**, *italic*, ~~gone~~, `code`, and [a link](https://example.com).

## Section

- item one
  - nested item
    1. deep ordered
- item two

1. first
2. second

> quoted line

```python
print("hi")
```

---
"""

DIALECTS = {
    "org": (md.markdown_to_org, md.org_to_markdown),
    "mediawiki": (md.markdown_to_mediawiki, md.mediawiki_to_markdown),
    "jira": (md.markdown_to_jira, md.jira_to_markdown),
}


def test_exports() -> None:
    for name in (
        "markdown_to_slack_mrkdwn",
        "slack_mrkdwn_to_markdown",
        "chat_messages_to_markdown",
        "markdown_to_chat_messages",
        "markdown_to_org",
        "org_to_markdown",
        "markdown_to_mediawiki",
        "mediawiki_to_markdown",
        "markdown_to_jira",
        "jira_to_markdown",
        "CHAT_ROLES",
    ):
        assert name in md.__all__


@pytest.mark.parametrize("name", sorted(DIALECTS))
def test_canonical_markdown_round_trips(name: str) -> None:
    to_dialect, to_markdown = DIALECTS[name]
    assert to_markdown(to_dialect(CANONICAL)) == CANONICAL


@pytest.mark.parametrize("name", sorted(DIALECTS))
def test_dialect_output_is_a_fixed_point(name: str) -> None:
    to_dialect, to_markdown = DIALECTS[name]
    once = to_dialect(CANONICAL)
    assert to_dialect(to_markdown(once)) == once


@pytest.mark.parametrize("name", sorted(DIALECTS) + ["slack"])
def test_empty_input(name: str) -> None:
    to_dialect, to_markdown = DIALECTS.get(name, (md.markdown_to_slack_mrkdwn, md.slack_mrkdwn_to_markdown))
    assert to_dialect("") == ""
    assert to_markdown("") == ""


def test_markup_inside_code_is_never_converted() -> None:
    source = "Use `**not bold**` and `[x](y)`.\n\n```\n**raw** *raw*\n```\n"
    for name, (to_dialect, to_markdown) in DIALECTS.items():
        assert to_markdown(to_dialect(source)) == source, name


# --- Org ----------------------------------------------------------------------

def test_org_forward_shapes() -> None:
    out = md.markdown_to_org(CANONICAL)
    assert "* Title" in out.splitlines()
    assert "** Section" in out.splitlines()
    assert "Intro with *bold*, /italic/, +gone+, ~code~, and [[https://example.com][a link]]." in out
    assert "#+BEGIN_SRC python" in out and "#+END_SRC" in out
    assert "#+BEGIN_QUOTE\nquoted line\n#+END_QUOTE" in out
    assert "1. first\n2. second" in out


def test_org_src_lines_starting_with_star_are_comma_escaped() -> None:
    source = "```\n* looks like a heading\n#+TITLE: x\n```\n"
    org = md.markdown_to_org(source)
    assert ",* looks like a heading" in org
    assert ",#+TITLE: x" in org
    assert md.org_to_markdown(org) == source


def test_org_reads_example_blocks_verbatim_and_plain_links() -> None:
    org = "#+begin_example\nkeep *this*\n#+end_example\nSee [[https://a.example]] and =verb=.\n"
    assert md.org_to_markdown(org) == "```\nkeep *this*\n```\nSee <https://a.example> and `verb`.\n"


def test_org_urls_in_text_are_not_read_as_italic() -> None:
    assert md.org_to_markdown("see https://a.example/b/c now\n") == "see https://a.example/b/c now\n"


# --- MediaWiki ----------------------------------------------------------------

def test_mediawiki_forward_shapes() -> None:
    out = md.markdown_to_mediawiki(CANONICAL)
    lines = out.splitlines()
    assert "= Title =" in lines and "== Section ==" in lines
    assert "Intro with '''bold''', ''italic'', <s>gone</s>, <code>code</code>, and [https://example.com a link]." in lines
    assert "* item one" in lines and "** nested item" in lines and "**# deep ordered" in lines
    assert '<syntaxhighlight lang="python">' in lines


def test_mediawiki_bold_italic_and_internal_links() -> None:
    wiki = "'''''both''''' and [[Main Page|home]] and [https://x.example]\n"
    assert md.mediawiki_to_markdown(wiki) == "***both*** and [[Main Page|home]] and <https://x.example>\n"


def test_mediawiki_pre_and_source_blocks() -> None:
    wiki = '<source lang="bash">\necho hi\n</source>\n<pre>\nplain\n</pre>\n'
    assert md.mediawiki_to_markdown(wiki) == "```bash\necho hi\n```\n```\nplain\n```\n"


# --- Jira ---------------------------------------------------------------------

def test_jira_forward_shapes() -> None:
    out = md.markdown_to_jira(CANONICAL)
    lines = out.splitlines()
    assert "h1. Title" in lines and "h2. Section" in lines
    assert "Intro with *bold*, _italic_, -gone-, {{code}}, and [a link|https://example.com]." in lines
    assert "{code:python}" in lines and "bq. quoted line" in lines


def test_jira_reads_code_options_noformat_quote_and_images() -> None:
    jira = (
        "{code:language=java|title=Demo}\nint x;\n{code}\n"
        "{noformat}\n*raw*\n{noformat}\n"
        "{quote}\nquoted *bold*\n{quote}\n"
        "!https://img.example/a.png|thumbnail! and - dash item\n"
    )
    assert md.jira_to_markdown(jira) == (
        "```java\nint x;\n```\n"
        "```\n*raw*\n```\n"
        "> quoted **bold**\n"
        "![](https://img.example/a.png) and - dash item\n"
    )


def test_jira_does_not_misread_ordinary_punctuation() -> None:
    text = "wow!great! 1-2-3 and a - b - c, well-known\n"
    assert md.jira_to_markdown(text) == text


def test_jira_dash_list_items() -> None:
    assert md.jira_to_markdown("- a\n- b\n") == "- a\n- b\n"


# --- Slack --------------------------------------------------------------------

SLACK_CANONICAL = """Intro with **bold**, *italic*, ~~gone~~, `code`, and [a link](https://example.com) & <https://x.y>.

- item one
  - nested item
- item two

1. first
2. second

> quoted line

```
if a < b && c > d:
```
"""


def test_slack_round_trip_on_its_subset() -> None:
    assert md.slack_mrkdwn_to_markdown(md.markdown_to_slack_mrkdwn(SLACK_CANONICAL)) == SLACK_CANONICAL


def test_slack_forward_shapes_and_escaping() -> None:
    out = md.markdown_to_slack_mrkdwn(SLACK_CANONICAL)
    assert "Intro with *bold*, _italic_, ~gone~, `code`, and <https://example.com|a link> &amp; <https://x.y>." in out
    assert "• item one\n    • nested item" in out
    assert "if a &lt; b &amp;&amp; c &gt; d:" in out


def test_slack_lossy_constructs_are_documented_shapes() -> None:
    out = md.markdown_to_slack_mrkdwn("# Head\n\n```python\nx\n```\n")
    assert out == "*Head*\n\n```\nx\n```\n"
    # A heading comes back as a bold paragraph; the fence language is gone.
    assert md.slack_mrkdwn_to_markdown(out) == "**Head**\n\n```\nx\n```\n"


def test_slack_mentions_stay_literal() -> None:
    assert md.slack_mrkdwn_to_markdown("hi <@U123> in <#C1|general> <!here>\n") == "hi <@U123> in <#C1|general> <!here>\n"


def test_slack_inline_code_unescapes_entities_on_round_trip() -> None:
    source = "Use `a<b && c>d` here\n"
    encoded = md.markdown_to_slack_mrkdwn(source)
    assert "`a&lt;b &amp;&amp; c&gt;d`" in encoded
    assert md.slack_mrkdwn_to_markdown(encoded) == source


# --- Chat messages ------------------------------------------------------------

MESSAGES = [
    {"role": "system", "content": "Be terse."},
    {"role": "user", "content": "## Summary\nhi\n```\n## User\n```"},
    {"role": "assistant", "content": ""},
    {"role": "tool", "content": '{"ok": true}'},
]


def test_chat_messages_round_trip() -> None:
    rendered = md.chat_messages_to_markdown(MESSAGES)
    assert rendered.startswith("## System\n\nBe terse.\n\n## User\n\n## Summary\n")
    assert md.markdown_to_chat_messages(rendered) == MESSAGES
    assert md.chat_messages_to_markdown(md.markdown_to_chat_messages(rendered)) == rendered


def test_chat_headings_are_case_insensitive_and_other_headings_are_content() -> None:
    parsed = md.markdown_to_chat_messages("## USER\nhello\n## Notes\nmore\n## assistant\nok\n")
    assert parsed == [
        {"role": "user", "content": "hello\n## Notes\nmore"},
        {"role": "assistant", "content": "ok"},
    ]


@pytest.mark.parametrize(
    "messages",
    [
        [{"role": "user", "content": "hi", "name": "bob"}],
        [{"role": "robot", "content": "hi"}],
        [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        [{"role": "user", "content": "before\n## Assistant\nafter"}],
        ["not a dict"],
    ],
)
def test_chat_rejects_unsupported_or_ambiguous_messages(messages: list) -> None:
    with pytest.raises(ValueError):
        md.chat_messages_to_markdown(messages)


def test_chat_rejects_text_before_first_role() -> None:
    with pytest.raises(ValueError, match="before the first role"):
        md.markdown_to_chat_messages("preamble\n## User\nhi\n")


@pytest.mark.parametrize("fence", ["```py", "~~~py"])
def test_chat_rejects_unclosed_fence_before_messages_can_merge(fence: str) -> None:
    messages = [
        {"role": "user", "content": f"{fence}\nprint(1)"},
        {"role": "assistant", "content": "hi"},
    ]
    with pytest.raises(ValueError, match="unclosed fenced code"):
        md.chat_messages_to_markdown(messages)


def test_placeholder_like_input_is_left_alone() -> None:
    text = "odd \ue0010\ue002 and \ue000B chars *b*\n"
    assert md.jira_to_markdown(text) == "odd \ue0010\ue002 and \ue000B chars **b**\n"
    assert md.jira_to_markdown("{{a\ue000Bb}}\n") == "`a\ue000Bb`\n"
    # A forged placeholder in the input stays literal; nested stashes resolve.
    assert md.jira_to_markdown("[{{x}} *y*|https://a.example] \ue000P0; tail\n") == (
        "[`x` **y**](https://a.example) \ue000P0; tail\n"
    )


def test_chat_roles_constant() -> None:
    assert md.CHAT_ROLES == ("system", "developer", "user", "assistant", "tool")


@pytest.mark.parametrize(
    "writer",
    [md.markdown_to_slack_mrkdwn, md.markdown_to_org, md.markdown_to_mediawiki, md.markdown_to_jira],
)
@pytest.mark.parametrize("url", ["javascript:alert%281%29", "shell:rm%20-rf", "data:text/html,x"])
def test_dialect_writers_drop_unsafe_link_schemes(writer, url: str) -> None:
    out = writer(f"see [label]({url}) and ![alt]({url})\n")
    assert url.split(":")[0] + ":" not in out
    assert "label" in out and "alt" in out
    assert "https://ok.example" in writer("[ok](https://ok.example)\n")


def test_org_and_jira_readers_drop_unsafe_link_schemes() -> None:
    assert md.org_to_markdown("[[javascript:alert(1)][click]]\n") == "click\n"
    assert md.org_to_markdown("[[https://ok.example][ok]]\n") == "[ok](https://ok.example)\n"
    assert "](javascript:" not in md.jira_to_markdown("!javascript:alert(1).png!\n")
    assert md.jira_to_markdown("!pic.png!\n") == "![](pic.png)\n"


# ═══ · kramdown ══════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_kramdown_helpers_exported() -> None:
    for name in (
        "ial",
        "with_attributes",
        "markdown_to_kramdown",
        "kramdown_to_markdown",
    ):
        assert name in md.__all__
        assert hasattr(md, name)


def test_ial_and_with_attributes_shape() -> None:
    assert md.ial() == ""
    assert md.ial(id="intro", classes="hero") == "{: #intro .hero}\n"
    assert (
        md.ial(id="box", classes=["note", "wide"], role="note")
        == '{: #box .note .wide role="note"}\n'
    )
    assert md.ial(id="#intro", classes=".hero") == "{: #intro .hero}\n"
    assert (
        md.with_attributes(md.heading("Title"), id="intro", classes="hero")
        == "# Title\n{: #intro .hero}\n"
    )
    assert md.with_attributes("Hello", id="lead") == "Hello\n{: #lead}\n"
    assert md.with_attributes("# Title\n") == "# Title\n"


def test_ial_rejects_broken_tokens() -> None:
    try:
        md.ial(id="has space")
    except ValueError as exc:
        assert "id" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    try:
        md.ial(**{"bad key": "x"})
    except ValueError as exc:
        assert "key" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_markdown_to_kramdown_heading_and_paragraph() -> None:
    src = "# Title {#intro .hero}\n\nHello world {#lead role=note}\n"
    out = md.markdown_to_kramdown(src)
    assert out.splitlines() == [
        "# Title",
        "{: #intro .hero}",
        "",
        "Hello world",
        '{: #lead role="note"}',
    ]


def test_markdown_to_kramdown_normalizes_existing_ial() -> None:
    src = "# Title {:#intro.hero}\n\n{:.box}\n"
    out = md.markdown_to_kramdown(src)
    assert "# Title" in out
    assert "{: #intro .hero}" in out
    assert "{: .box}" in out
    assert "{:#intro.hero}" not in out


def test_markdown_to_kramdown_leaves_ordinary_markdown() -> None:
    src = (
        "# Title\n\n"
        "A paragraph with **bold** and [a](https://ex.com).\n\n"
        "- item\n\n"
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
        "> quote\n\n"
        "```\n{#not-an-ial}\n```\n"
    )
    assert md.markdown_to_kramdown(src) == src


def test_kramdown_to_markdown_strips_known_ial() -> None:
    src = "# Title\n{: #intro .hero}\n\nHello\n{: #lead}\n"
    out = md.kramdown_to_markdown(src)
    assert out.splitlines() == ["# Title", "", "Hello"]
    assert "{:" not in out
    assert "{#intro}" not in out


def test_kramdown_to_markdown_strips_inline_ial() -> None:
    out = md.kramdown_to_markdown("# Title {: #intro}\n")
    assert out == "# Title\n"


def test_round_trip_ial_subset_is_lossy_on_attributes() -> None:
    src = "# Title {#intro .hero}\n\nHello {#lead}\n"
    kd = md.markdown_to_kramdown(src)
    assert "{: #intro .hero}" in kd
    assert "{: #lead}" in kd
    back = md.kramdown_to_markdown(kd)
    assert back.splitlines() == ["# Title", "", "Hello"]
    assert md.kramdown_to_markdown(md.markdown_to_kramdown("# Plain\n")) == "# Plain\n"


def test_unknown_kramdown_and_liquid_stay_literal() -> None:
    src = (
        "{::comment}\nhidden\n{:/comment}\n\n"
        "* TOC\n{:toc}\n\n"
        "---\ntitle: Page\n---\n\n"
        "{% include header.html %}\n"
        "{{ page.title }}\n"
    )
    assert md.markdown_to_kramdown(src) == src
    assert md.kramdown_to_markdown(src) == src


def test_list_and_table_trailing_attrs_are_not_rewritten() -> None:
    src = "- item {#id}\n\n| a | b | {#t}\n| --- | --- |\n"
    assert md.markdown_to_kramdown(src) == src


def test_fenced_ial_example_stays_code() -> None:
    src = "```\n# Title {#intro}\n{: #intro}\n```\n"
    assert md.markdown_to_kramdown(src) == src
    assert md.kramdown_to_markdown(src) == src


def test_html_to_markdown_to_kramdown_chain() -> None:
    html = (
        '<h1 id="intro" class="hero">Title</h1>'
        '<p id="lead">Hello <strong>world</strong>.</p>'
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    )
    mid = md.html_to_markdown(html)
    assert "# Title {#intro .hero}" in mid
    assert "Hello **world**." in mid
    assert "{#lead}" in mid
    assert "| a | b |" in mid
    assert "| 1 | 2 |" in mid

    kd = md.markdown_to_kramdown(mid)
    assert "{: #intro .hero}" in kd
    assert "{: #lead}" in kd
    assert "# Title {#intro" not in kd
    assert "| 1 | 2 |" in kd
    assert "**world**" in kd


def test_html_heading_without_attrs_stays_plain() -> None:
    assert md.html_to_markdown("<h1>Title</h1>").startswith("# Title")
    assert "{#" not in md.html_to_markdown("<h1>Title</h1>")


def test_kramdown_to_markdown_to_html_chain() -> None:
    kd = "# Title\n{: #intro .hero}\n\nHello **world**.\n{: #lead}\n"
    plain = md.kramdown_to_markdown(kd)
    assert "{:" not in plain
    html = md.markdown_to_html(plain)
    assert "<h1>Title</h1>" in html
    assert "<strong>world</strong>" in html
    assert "intro" not in html


def test_markdown_to_html_does_not_apply_ial() -> None:
    html = md.markdown_to_html("# Title\n{: #intro}\n")
    assert "<h1>Title</h1>" in html
    assert 'id="intro"' not in html


# ═══ · generation ════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_heading_levels_clamped() -> None:
    assert md.heading("Title") == "# Title\n"
    assert md.heading("Sub", level=2) == "## Sub\n"
    assert md.heading("Deep", level=0) == "# Deep\n"
    assert md.heading("Deep", level=99) == "###### Deep\n"


def test_inline_decorations() -> None:
    assert md.bold("x") == "**x**"
    assert md.italic("x") == "*x*"
    assert md.strikethrough("x") == "~~x~~"


def test_blockquote_multiline() -> None:
    assert md.blockquote("a\nb") == "> a\n> b\n"
    assert md.blockquote("a\n\nb") == "> a\n>\n> b\n"


def test_horizontal_rule() -> None:
    assert md.horizontal_rule() == "---\n"


def test_bullet_and_numbered_list() -> None:
    assert md.bullet_list(["a", "b"]) == "- a\n- b\n"
    assert md.bullet_list([]) == ""
    assert md.numbered_list(["a", "b"]) == "1. a\n2. b\n"


def test_task_item_and_task_list() -> None:
    assert md.task_item("todo") == "- [ ] todo\n"
    assert md.task_item("done", checked=True) == "- [x] done\n"
    assert md.task_list(["a", ("b", True)]) == "- [ ] a\n- [x] b\n"
    assert md.task_list([]) == ""


def test_details_and_footnote_generators() -> None:
    assert md.details("More", "hidden") == ":::details More\nhidden\n:::\n"
    assert md.footnote_ref("1") == "[^1]"
    assert md.footnote("1", "note") == "[^1]: note\n"


def test_inline_code() -> None:
    assert md.inline_code("x = 1") == "`x = 1`"


def test_code_block() -> None:
    assert md.code_block("print(1)", lang="python") == "```python\nprint(1)\n```\n"
    assert md.code_block("plain") == "```\nplain\n```\n"


def test_json_block() -> None:
    out = md.json_block({"a": 1})
    assert out.startswith("```json\n")
    assert out.endswith("```\n")
    assert '"a": 1' in out


def test_status_line() -> None:
    assert md.status_line(True, "all good", "broken") == "✓ all good\n"
    assert md.status_line(False, "all good", "broken") == "⚠ broken\n"


def test_table_basic_and_padding() -> None:
    out = md.table(["a", "b"], [[1, 2], [3]])
    assert out == "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 |  |\n"
    assert md.table([], [["x"]]) == ""


def test_key_value_table() -> None:
    out = md.key_value_table({"mode": "train", "epochs": 10})
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| epochs | 10 |\n"


def test_md_table_header_and_rows() -> None:
    out = md.md_table(["name", "val"], ["loss", "0.01"], ["iou", "0.85"])
    assert out == "| name | val |\n| --- | --- |\n| loss | 0.01 |\n| iou | 0.85 |\n"


def test_md_table_dict_records() -> None:
    out = md.md_table({"name": "loss", "val": "0.01"}, {"name": "iou", "val": "0.85"})
    assert out == "| name | val |\n| --- | --- |\n| loss | 0.01 |\n| iou | 0.85 |\n"


def test_md_table_scalar_fallback_and_empty() -> None:
    assert md.md_table("a", "b") == "| value |\n| --- |\n| a |\n| b |\n"
    assert md.md_table() == ""


def test_md_kv_alternating_and_dict_mixed() -> None:
    out = md.md_kv("mode", "train", "epochs", 10)
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| epochs | 10 |\n"
    out2 = md.md_kv({"mode": "train"}, "device", "cuda")
    assert out2 == "| Key | Value |\n| --- | --- |\n| mode | train |\n| device | cuda |\n"


def test_md_kv_trailing_key_without_value() -> None:
    out = md.md_kv("mode", "train", "orphan")
    assert out == "| Key | Value |\n| --- | --- |\n| mode | train |\n| orphan |  |\n"


def test_section_joins_blocks() -> None:
    out = md.section("Summary", [md.bullet_list(["ok"]), md.horizontal_rule()])
    assert out == "## Summary\n" + "- ok\n" + "---\n"
    assert md.section("Top", ["body\n"], level=1) == "# Top\nbody\n"


def test_section_inserts_a_newline_before_a_block_that_would_otherwise_run_on() -> None:
    # A caller-supplied block with no trailing newline of its own (plain
    # prose, unlike every builder above) must not run directly into the
    # next block's leading syntax -- that used to turn a following bullet
    # list's first "- item" into plain text glued onto the prior sentence.
    out = md.section("Report", ["Intro sentence.", md.bullet_list(["one", "two"])])
    assert out == "## Report\nIntro sentence.\n- one\n- two\n"
    html = md.markdown_to_html(out)
    assert "<li>one</li>" in html
    assert "Intro sentence.- one" not in html


def test_wrap_section_markers() -> None:
    out = md.wrap_section("PATHS_TRACE", "body\n")
    assert out == "<!-- BEGIN_SECTION:PATHS_TRACE -->\nbody\n<!-- END_SECTION:PATHS_TRACE -->\n"


def test_generation_functions_exposed_in_all() -> None:
    for name in (
        "heading",
        "bold",
        "italic",
        "strikethrough",
        "blockquote",
        "alert",
        "horizontal_rule",
        "bullet_list",
        "numbered_list",
        "task_item",
        "task_list",
        "details",
        "footnote_ref",
        "footnote",
        "inline_code",
        "code_block",
        "json_block",
        "table",
        "key_value_table",
        "md_table",
        "md_kv",
        "status_line",
        "section",
        "wrap_section",
        "alert_stylesheet",
        "default_stylesheet",
        "ial",
        "with_attributes",
        "markdown_to_kramdown",
        "kramdown_to_markdown",
    ):
        assert name in md.__all__
        assert hasattr(md, name)


# ═══ · mermaid helpers ═══════════════════════════════════════════════════════════════════════════════════

def test_mermaid_block_round_trip_and_unicode():
    source = "flowchart TD\n  A[開始] --> B[完了]"
    wrapped = md.mermaid_block(source)

    assert wrapped.startswith("```mermaid\n")
    assert md.extract_mermaid_blocks(wrapped) == [source]


def test_mermaid_block_uses_adaptive_fence_for_backticks():
    source = "sequenceDiagram\n  Note over A: contains ``` here"
    wrapped = md.mermaid_block(source)

    assert wrapped.startswith("````mermaid\n")
    assert md.extract_mermaid_blocks(wrapped) == [source]


def test_extract_mermaid_blocks_keeps_order_and_ignores_other_code():
    document = (
        md.mermaid_block("flowchart LR\n  A --> B")
        + md.code_block("print(1)", lang="python")
        + md.mermaid_block("classDiagram\n  class User")
    )

    assert md.extract_mermaid_blocks(document) == [
        "flowchart LR\n  A --> B",
        "classDiagram\n  class User",
    ]


def test_mermaid_language_match_is_case_insensitive():
    document = "```MERMAID\nflowchart TD\n  A --> B\n```\n"
    assert md.extract_mermaid_blocks(document) == ["flowchart TD\n  A --> B"]


def test_inline_code_and_non_mermaid_fences_are_ignored():
    document = (
        "Use `mermaid` inline.\n\n"
        "```text\nmermaid\n```\n"
    )
    assert md.extract_mermaid_blocks(document) == []


def test_mermaid_block_normalizes_crlf_and_lone_cr():
    source = "flowchart TD\r\n  A --> B\r  B --> C\r\n"
    wrapped = md.mermaid_block(source)

    assert "\r" not in wrapped
    assert md.extract_mermaid_blocks(wrapped) == [
        "flowchart TD\n  A --> B\n  B --> C\n"
    ]


def test_empty_mermaid_source_round_trips():
    assert md.extract_mermaid_blocks(md.mermaid_block("")) == [""]


def test_public_exports_include_mermaid_helpers():
    assert "mermaid_block" in md.__all__
    assert "extract_mermaid_blocks" in md.__all__


# ═══ · structural diagrams ═══════════════════════════════════════════════════════════════════════════════

def test_heading_tree_to_mermaid_mindmap_ignores_fenced_headings():
    source = (
        "# Root\n"
        "## Child\n"
        "~~~text\n"
        "# not a heading\n"
        "~~~\n"
        "### Grandchild\n"
        "# Next\n"
    )

    assert md.markdown_headings_to_mermaid_mindmap(source, root="Doc") == (
        "mindmap\n"
        '  root["Doc"]\n'
        '    n0["Root"]\n'
        '      n1["Child"]\n'
        '        n2["Grandchild"]\n'
        '    n3["Next"]\n'
    )


def test_task_dependencies_to_mermaid_flowchart():
    source = (
        "- [ ] Build\n"
        "- [x] Test <- Build\n"
        "- [ ] Deploy <- Test, Build\n"
    )

    assert md.markdown_tasks_to_mermaid_flowchart(source) == (
        "flowchart TD\n"
        '  n0["Build"]\n'
        '  n1["Test"]\n'
        '  n2["Deploy"]\n'
        "  n0 --> n1\n"
        "  n1 --> n2\n"
        "  n0 --> n2\n"
    )


def test_task_dependency_rejects_unknown_and_cycles():
    with pytest.raises(ValueError, match="Unknown task dependencies"):
        md.markdown_tasks_to_mermaid_flowchart("- [ ] Deploy <- Build\n")

    cyclic = "- [ ] A <- B\n- [ ] B <- A\n"
    with pytest.raises(ValueError, match="cycle"):
        md.markdown_tasks_to_mermaid_flowchart(cyclic)


def test_task_dependencies_ignore_fenced_examples():
    source = (
        "- [ ] Real\n"
        "~~~markdown\n"
        "- [ ] Fake <- Real\n"
        "~~~\n"
    )
    result = md.markdown_tasks_to_mermaid_flowchart(source)
    assert 'n0["Real"]' in result
    assert "Fake" not in result


def test_python_ast_to_mermaid_class_diagram():
    source = (
        "class Base:\n"
        "    def ping(self, value):\n"
        "        return value\n"
        "\n"
        "class Child(Base):\n"
        "    async def run(self, item):\n"
        "        return item\n"
    )

    assert md.python_to_mermaid_class_diagram(source) == (
        "classDiagram\n"
        '  class c0["Base"] {\n'
        "    ping(value)\n"
        "  }\n"
        '  class c1["Child"] {\n'
        "    run(item)\n"
        "  }\n"
        "  c0 <|-- c1\n"
    )


def test_python_class_diagram_includes_external_base_and_rejects_invalid_source():
    result = md.python_to_mermaid_class_diagram("class Child(pkg.Base):\n    pass\n")
    assert 'class c1["pkg.Base"]' in result
    assert "c1 <|-- c0" in result

    with pytest.raises(ValueError, match="Invalid Python source"):
        md.python_to_mermaid_class_diagram("class broken(")


def test_markdown_links_to_dot_tracks_heading_context_and_ignores_code():
    source = (
        "# Intro\n"
        "[Docs](https://example.com/docs)\n"
        "`[inline](https://ignored.example)`\n"
        "~~~markdown\n"
        "[fenced](https://ignored.example/fenced)\n"
        "~~~\n"
        "## More\n"
        "[Ref][site]\n"
        "\n"
        "[site]: https://example.com/ref\n"
    )

    assert md.markdown_links_to_dot(source) == (
        "digraph markdown_links {\n"
        '  s0 [label="Intro"];\n'
        '  s1 [label="More"];\n'
        '  u0 [label="https://example.com/docs"];\n'
        '  u1 [label="https://example.com/ref"];\n'
        '  s0 -> u0 [label="Docs"];\n'
        '  s1 -> u1 [label="Ref"];\n'
        "}\n"
    )


def test_structural_diagram_outputs_are_deterministic():
    heading_source = "# A\n## B\n"
    task_source = "- [ ] A\n- [ ] B <- A\n"
    python_source = "class A:\n    pass\n"
    link_source = "# A\n[x](https://example.com)\n"

    calls = [
        (md.markdown_headings_to_mermaid_mindmap, heading_source),
        (md.markdown_tasks_to_mermaid_flowchart, task_source),
        (md.python_to_mermaid_class_diagram, python_source),
        (md.markdown_links_to_dot, link_source),
    ]
    for func, source in calls:
        assert func(source) == func(source)


def test_markdown_links_to_dot_empty_heading_falls_back_to_document():
    source = "# \n[Docs](https://example.com/docs)\n"

    assert md.markdown_links_to_dot(source) == (
        "digraph markdown_links {\n"
        '  s0 [label="Document"];\n'
        '  u0 [label="https://example.com/docs"];\n'
        '  s0 -> u0 [label="Docs"];\n'
        "}\n"
    )


# ═══ · directory tree ════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DIRECTORY_TREE_CANONICAL = "- src/\n  - app.py\n  - utils/\n    - __init__.py\n- README.md\n"
TREE = {"src": {"app.py": None, "utils": {"__init__.py": None}}, "README.md": None}


def test_exports_directory_tree() -> None:
    for name in (
        "markdown_to_directory_tree",
        "directory_tree_to_markdown",
        "directory_to_markdown",
        "tree_text_to_markdown",
        "markdown_to_tree_text",
        "scaffold_from_markdown",
    ):
        assert name in md.__all__


def test_markdown_list_round_trips_through_tree_data() -> None:
    assert md.markdown_to_directory_tree(DIRECTORY_TREE_CANONICAL) == TREE
    assert md.directory_tree_to_markdown(TREE) == DIRECTORY_TREE_CANONICAL


def test_item_with_children_is_a_directory_even_without_slash() -> None:
    tree = md.markdown_to_directory_tree("- src\n  - app.py\n- empty/\n")
    assert tree == {"src": {"app.py": None}, "empty": {}}


def test_inline_code_labels_four_space_indent_and_fences_are_handled() -> None:
    content = (
        "Layout:\n\n"
        "* `pkg/`\n"
        "    * `__init__.py`\n"
        "\n"
        "```text\n"
        "- not/a/real/entry\n"
        "```\n"
    )
    assert md.markdown_to_directory_tree(content) == {"pkg": {"__init__.py": None}}


@pytest.mark.parametrize(
    "bad",
    [
        "- ../evil\n", "- a/b\n", "- .\n", "- a\\b\n", "- a\x01b\n",
        "- \\ a\n", "- `` `x` ``\n",
    ],
)
def test_unsafe_names_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        md.markdown_to_directory_tree(bad)


@pytest.mark.parametrize("bad", [" a", "a ", "`x`", "a\tb", "a\nb"])
def test_tree_writer_rejects_names_that_would_read_back_differently(bad: str) -> None:
    with pytest.raises(ValueError):
        md.directory_tree_to_markdown({bad: None})


@pytest.mark.parametrize("ok", ["console", "COM10", "lpt", "a.b.c", ".env", "CONFIG.md"])
def test_portable_names_near_reserved_ones_are_accepted(ok: str) -> None:
    assert md.markdown_to_directory_tree(f"- {ok}\n") == {ok: None}


NON_PORTABLE_NAMES = ["a:b", "CON", "con.txt", "Com1", "lpt9.log", "nul .txt", "name.", "a?b", "a|b"]


@pytest.mark.parametrize("name", NON_PORTABLE_NAMES)
def test_scaffold_rejects_non_portable_names_before_creating_anything(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="portable"):
        md.scaffold_from_markdown(f"- ok/\n  - {name}\n", tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", NON_PORTABLE_NAMES)
def test_read_only_tree_functions_accept_posix_names(name: str) -> None:
    # Portability is a scaffold concern; parsing and rendering stay lossless.
    tree = md.markdown_to_directory_tree(f"- {name}\n")
    assert tree == {name: None}
    assert md.markdown_to_directory_tree(md.directory_tree_to_markdown(tree)) == tree


def test_directory_to_markdown_lists_posix_only_names(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").touch()
    (tmp_path / "log-12:00.txt").touch()
    (tmp_path / "aux").touch()
    assert md.directory_to_markdown(tmp_path) == "- aux\n- log-12:00.txt\n- ok.txt\n"


def test_tree_text_keeps_only_symlink_names() -> None:
    text = ".\n├── bin -> /usr/bin\n└── pkg\n    └── link.py -> ../x.py\n"
    assert md.tree_text_to_markdown(text) == "- bin\n- pkg/\n  - link.py\n"


def test_duplicate_entries_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        md.markdown_to_directory_tree("- a.txt\n- a.txt\n")


def test_tree_text_round_trip_unicode() -> None:
    text = md.markdown_to_tree_text(DIRECTORY_TREE_CANONICAL)
    assert text == (
        ".\n"
        "├── src/\n"
        "│   ├── app.py\n"
        "│   └── utils/\n"
        "│       └── __init__.py\n"
        "└── README.md\n"
    )
    assert md.tree_text_to_markdown(text) == DIRECTORY_TREE_CANONICAL


def test_tree_text_accepts_ascii_connectors_and_ignores_summary() -> None:
    text = ".\n|-- src\n|   `-- app.py\n`-- README.md\n\n1 directory, 2 files\n"
    assert md.tree_text_to_markdown(text) == "- src/\n  - app.py\n- README.md\n"


def test_tree_text_misaligned_levels_raise() -> None:
    with pytest.raises(ValueError, match="aligned"):
        md.tree_text_to_markdown(".\n  ├── bad\n")


def test_directory_to_markdown_is_sorted_and_skips_hidden(tmp_path: Path) -> None:
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "x.txt").write_text("", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    assert md.directory_to_markdown(tmp_path) == "- a.txt\n- b/\n  - x.txt\n"
    assert ".git/" in md.directory_to_markdown(tmp_path, include_hidden=True)
    assert md.directory_to_markdown(tmp_path, max_depth=1) == "- a.txt\n- b/\n"


def test_directory_to_markdown_rejects_non_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        md.directory_to_markdown(tmp_path / "missing")


def test_scaffold_creates_tree_and_is_idempotent(tmp_path: Path) -> None:
    created = md.scaffold_from_markdown(DIRECTORY_TREE_CANONICAL, tmp_path)
    assert created == ["src/", "src/app.py", "src/utils/", "src/utils/__init__.py", "README.md"]
    assert (tmp_path / "src" / "utils" / "__init__.py").is_file()
    assert md.scaffold_from_markdown(DIRECTORY_TREE_CANONICAL, tmp_path) == []
    # Scaffold -> directory -> Markdown closes the loop (sorted listing).
    assert md.markdown_to_directory_tree(md.directory_to_markdown(tmp_path)) == TREE


def test_scaffold_never_overwrites_existing_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("keep me", encoding="utf-8")
    md.scaffold_from_markdown("- README.md\n", tmp_path)
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "keep me"


def test_scaffold_file_directory_collision_raises(tmp_path: Path) -> None:
    (tmp_path / "src").write_text("", encoding="utf-8")
    with pytest.raises(FileExistsError):
        md.scaffold_from_markdown("- src/\n  - app.py\n", tmp_path)


def test_scaffold_rejects_traversal_before_creating_anything(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        md.scaffold_from_markdown("- ok.txt\n- ../escape.txt\n", tmp_path)
    assert not (tmp_path / "ok.txt").exists()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_scaffold_collision_is_detected_before_anything_is_created(tmp_path: Path) -> None:
    (tmp_path / "b").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        md.scaffold_from_markdown("- a/\n  - x\n- b/\n  - y\n", tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["b"]
    assert (tmp_path / "b").read_text(encoding="utf-8") == "keep"


def test_scaffold_does_not_create_root_when_validation_fails(tmp_path: Path) -> None:
    root = tmp_path / "new-root"
    with pytest.raises(ValueError):
        md.scaffold_from_markdown("- CON\n", root)
    assert not root.exists()


# ═══ · stylesheets ═══════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_stylesheet_helpers_exported() -> None:
    assert "alert_stylesheet" in md.__all__
    assert "default_stylesheet" in md.__all__


def test_alert_stylesheet_is_nonempty_and_has_hooks() -> None:
    css = md.alert_stylesheet()
    assert css.strip()
    assert ".markdown-alert" in css
    assert ".markdown-alert-title" in css
    assert ".markdown-alert-note" in css
    assert 'data-alert-flavor="github"' in css
    assert "url(" not in css
    assert "http://" not in css
    assert "https://" not in css


def test_default_stylesheet_includes_alerts_and_common_blocks() -> None:
    alert = md.alert_stylesheet()
    css = md.default_stylesheet()
    assert css.strip()
    assert alert in css
    assert "table" in css
    assert "blockquote" in css
    assert "pre" in css
    assert "code" in css
    assert "del" in css
    assert "checkbox" in css
    assert "details" in css
    assert "summary" in css
    assert "footnotes" in css
    assert re.search(r"\bh1\b", css)
    assert "url(" not in css
    assert "http://" not in css
    assert "https://" not in css


def test_readme_embed_pattern_is_valid_html() -> None:
    src = md.section("Summary", [md.table(["a", "b"], [[1, 2]]), md.blockquote("quoted")])
    html = "<style>" + md.default_stylesheet() + "</style>\n" + md.markdown_to_html(src)
    assert html.startswith("<style>")
    assert "</style>" in html
    assert "<table>" in html
    assert "<blockquote>" in html


# ═══ · scanner contract ══════════════════════════════════════════════════════════════════════════════════
# Contracts for the shared Markdown line scanner (Hub-P0).

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_scanner_marks_adaptive_fence_and_its_contents() -> None:
    lines = ["````markdown", "```nested", "```", "````", "outside"]
    scanned = md._scan_lines(lines)

    assert [line.in_fenced_code for line in scanned] == [True, True, True, True, False]
    assert [line.is_fence_open for line in scanned] == [True, False, False, False, False]
    assert [line.is_fence_close for line in scanned] == [False, False, False, True, False]


def test_scanner_handles_tilde_fences_independently() -> None:
    scanned = md._scan_lines(["~~~python", "```not a closer", "~~~", "text"])
    assert [line.in_fenced_code for line in scanned] == [True, True, True, False]
    assert scanned[2].is_fence_close


def test_inline_code_mask_preserves_offsets_and_ignores_unclosed_runs() -> None:
    source = "[live](https://example.test) and `[not](https://hidden.test)` plus `open"
    masked = md._mask_inline_code(source)

    assert len(masked) == len(source)
    assert "https://example.test" in masked
    assert "https://hidden.test" not in masked
    assert "`open" in masked


def test_extract_code_blocks_uses_the_shared_adaptive_fence_contract() -> None:
    source = "````markdown\n```inner\n```\n````\n"
    assert md.extract_code_blocks(source) == [
        {"language": "markdown", "info": "markdown", "code": "```inner\n```"}
    ]


# ═══ · nul sanitization ══════════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("keep \x00PH0\x00 here and `code`", "<p>keep \ufffdPH0\ufffd here and <code>code</code></p>\n"),
        ("only \x00PH0\x00 text", "<p>only \ufffdPH0\ufffd text</p>\n"),
        ("```\n\x00\n```", "<pre><code>\ufffd\n</code></pre>\n"),
    ],
)
def test_markdown_to_html_replaces_input_nul(source: str, expected: str) -> None:
    result = md.markdown_to_html(source)
    assert result == expected
    assert "\x00" not in result


# ═══ · issue 63 followups ════════════════════════════════════════════════════════════════════════════════
# Regression tests for the follow-up issues in #63.

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_markdown_to_man_replaces_nul_in_body_and_rejects_header_controls() -> None:
    fence = "\x60\x60\x60"
    content = "paragraph before\x00after\n\n" + fence + "\ncode before\x00after\n" + fence
    out = md.markdown_to_man(content, name="demo")
    assert "\x00" not in out
    assert "paragraph before\uFFFDafter" in out
    assert "code before\uFFFDafter" in out
    with pytest.raises(ValueError, match="control characters"):
        md.markdown_to_man("", name="demo\x00name")


def test_compact_llm_output_preserves_info_string_and_is_idempotent() -> None:
    fence = "\x60\x60\x60"
    text = fence + "python title=example.py\nline1\nline2\nline3\nline4\n" + fence + "\n"
    compacted = md.compact_llm_output(text, max_code_lines=2)
    assert compacted.startswith(fence + "python title=example.py\n")
    assert "… 2 more lines" in compacted
    assert md.compact_llm_output(compacted, max_code_lines=2) == compacted


def test_split_reasoning_balances_nested_details() -> None:
    text = (
        "before\n"
        '<details type="reasoning">\n'
        "<summary>outer summary</summary>\n"
        "outer start\n"
        "<details><summary>inner summary</summary>inner body</details>\n"
        "outer end\n"
        "</details>\n"
        "after\n"
    )
    result = md.split_reasoning(text)
    assert result["formats"] == ["details"]
    assert "inner summary" in result["reasoning"][0]
    assert "inner body</details>" in result["reasoning"][0]
    assert result["reasoning"][0].endswith("outer end")
    assert result["answer"] == "before\n\nafter\n"


def test_markdown_to_chat_messages_preserves_non_lf_separators() -> None:
    text = (
        "## User\r\n"
        "first\rsecond\vthird\ffourth\u2028fifth\u2029sixth\n"
        "## Assistant\n"
        "ok\n"
    )
    messages = md.markdown_to_chat_messages(text)
    assert messages == [
        {"role": "user", "content": "first\rsecond\vthird\ffourth\u2028fifth\u2029sixth"},
        {"role": "assistant", "content": "ok"},
    ]


def test_directory_to_markdown_rejects_zero_max_depth(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_depth must be >= 1"):
        md.directory_to_markdown(tmp_path, max_depth=0)


def test_scanner_preserves_legacy_fence_close_with_trailing_text() -> None:
    fence = "\x60\x60\x60"
    scanned = md._scan_lines([fence, "inside", fence + "inner", "outside"])
    assert scanned[2].is_fence_close
    assert not scanned[3].in_fenced_code


def test_tree_text_treats_literal_arrow_name_as_ambiguous_symlink() -> None:
    assert md.tree_text_to_markdown("root\n└── report -> backup\n") == "- report\n"


def test_compact_llm_output_zero_limit_and_tilde_fence_are_idempotent() -> None:
    fence = "~~~"
    text = fence + "python title=example.py\nline1\nline2\n" + fence + "\n"
    compacted = md.compact_llm_output(text, max_code_lines=0)
    assert compacted.startswith(fence + "python title=example.py\n")
    assert "… 2 more lines" in compacted
    assert md.compact_llm_output(compacted, max_code_lines=0) == compacted


def test_split_reasoning_preserves_nested_summary_when_outer_has_none() -> None:
    text = (
        '<details type="reasoning">\n'
        "outer start\n"
        "<details><summary>inner summary</summary>inner body</details>\n"
        "outer end\n"
        "</details>\n"
        "answer\n"
    )
    result = md.split_reasoning(text)
    assert result["reasoning"] == [
        "outer start\n<details><summary>inner summary</summary>inner body</details>\nouter end"
    ]
    assert result["answer"] == "answer\n"


def test_split_reasoning_unclosed_nested_details_consumes_remainder() -> None:
    text = '<details type="reasoning">outer<details>inner</details>tail'
    result = md.split_reasoning(text)
    assert result["reasoning"] == ["outer<details>inner</details>tail"]
    assert result["answer"] == ""


if __name__ == "__main__":
    unittest.main()
