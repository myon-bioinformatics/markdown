from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

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
