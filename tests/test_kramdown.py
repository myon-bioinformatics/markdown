from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


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
