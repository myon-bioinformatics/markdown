"""🌐 HTML and Markdown in both directions: the lightweight DOM, malformed HTML, code newlines, data URIs, extraction, whitespace, context helpers, composition, fixtures and the JS mirror."""
from __future__ import annotations

import collections
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
import markdown as md


# ═══ · lightweight dom ═══════════════════════════════════════════════════════════════════════════════════

def test_supported_html_string_path_matches_dom_path():
    html = (
        '<h1 id="top">Title</h1>'
        '<p>Hello <strong>world</strong> and <a href="https://example.com">link</a>.</p>'
        '<ul><li>one</li><li><em>two</em></li></ul>'
    )
    assert md.dom_to_markdown(md.parse_html_dom(html)) == md.html_to_markdown(html)


def test_parse_html_dom_builds_normalized_public_tree():
    root = md.parse_html_dom('<P class="lead">Hello <strong>世界</strong></P>')
    assert root.kind == "root"
    assert root.children[0].tag == "p"
    assert root.children[0].attrs == {"class": "lead"}
    assert root.children[0].children[0].text == "Hello "
    assert root.children[0].children[1].tag == "strong"


def test_markdown_to_dom_to_markdown_semantic_normalization():
    source = "# Title\n\nHello **world**.\n\n- one\n- two\n"
    tree = md.markdown_to_dom(source)
    back = md.dom_to_markdown(tree)

    assert "# Title" in back
    assert "Hello **world**." in back
    assert "- one" in back
    assert "- two" in back


def test_nested_and_mixed_lists_survive_dom_path():
    html = (
        "<ul><li>outer<ol><li>first</li><li>second</li></ol></li>"
        "<li>tail</li></ul>"
    )
    back = md.dom_to_markdown(md.parse_html_dom(html))
    assert "- outer" in back
    assert "1. first" in back
    assert "2. second" in back
    assert "- tail" in back


def test_table_pipe_link_image_and_code_survive_dom_path():
    html = (
        "<table><thead><tr><th>name</th><th>value</th></tr></thead>"
        "<tbody><tr><td>a|b</td><td><code>x</code></td></tr></tbody></table>"
        '<p><a href="https://example.com">docs</a> '
        '<img src="/img.png" alt="pic"></p>'
    )
    back = md.dom_to_markdown(md.parse_html_dom(html))
    assert r"a\|b" in back
    assert "`x`" in back
    assert "[docs](https://example.com)" in back
    assert "![pic](/img.png)" in back


def test_details_summary_is_preserved_as_supported_markdown_container():
    html = "<details open><summary>More</summary><p>Body <strong>text</strong>.</p></details>"
    back = md.dom_to_markdown(md.parse_html_dom(html))
    assert back.startswith(":::details More\n")
    assert "Body **text**." in back
    assert back.rstrip().endswith(":::")


def test_script_style_event_and_style_attributes_are_dropped():
    html = (
        '<div onclick="evil()" style="color:red">'
        '<script>alert(1)</script><style>body{display:none}</style>'
        '<p id="safe" onmouseover="evil()">Visible</p></div>'
    )
    tree = md.parse_html_dom(html)
    sanitized = md.dom_to_html(tree)

    assert "script" not in sanitized
    assert "alert(1)" not in sanitized
    assert "style" not in sanitized
    assert "display:none" not in sanitized
    assert "onclick" not in sanitized
    assert "onmouseover" not in sanitized
    assert '<p id="safe">Visible</p>' in sanitized


def test_unsafe_url_schemes_are_removed_but_safe_urls_remain():
    html = (
        '<a href="javascript:alert(1)">bad</a>'
        '<a href="https://example.com">good</a>'
        '<img src="data:text/html,boom" alt="bad">'
        '<img src="/safe.png" alt="good">'
    )
    sanitized = md.dom_to_html(md.parse_html_dom(html))

    assert "javascript:" not in sanitized
    assert "data:text/html" not in sanitized
    assert 'href="https://example.com"' in sanitized
    assert 'src="/safe.png"' in sanitized


def test_unknown_tags_degrade_to_transparent_containers():
    tree = md.parse_html_dom("<custom-widget><p>Hello</p></custom-widget>")
    sanitized = md.dom_to_html(tree)

    assert "custom-widget" not in sanitized
    assert sanitized == "<p>Hello</p>"


def test_malformed_html_degrades_without_throwing():
    tree = md.parse_html_dom("<div><p>hello<strong> world</div>")
    sanitized = md.dom_to_html(tree)

    assert "hello" in sanitized
    assert "world" in sanitized
    assert "<div" not in sanitized


def test_checkbox_task_item_survives_dom_path():
    html = '<ul><li><input type="checkbox" checked disabled> done</li></ul>'
    back = md.dom_to_markdown(md.parse_html_dom(html))
    assert "- [x] done" in back


def test_dom_helpers_are_public_and_do_not_require_io_or_network():
    for name in (
        "HtmlNode",
        "parse_html_dom",
        "dom_to_html",
        "dom_to_markdown",
        "markdown_to_dom",
    ):
        assert name in md.__all__


def test_control_characters_cannot_bypass_url_scheme_checks():
    html = (
        '<a href="javascript\x00:alert(1)">nul</a>'
        '<a href="java\tscript:alert(1)">tab</a>'
        '<a href="java\nscript:alert(1)">newline</a>'
    )
    sanitized = md.dom_to_html(md.parse_html_dom(html))

    assert "javascript:" not in sanitized
    assert "java\x00script:" not in sanitized
    assert "java\tscript:" not in sanitized
    assert "java\nscript:" not in sanitized
    assert 'href=' not in sanitized


def test_shared_url_policy_applies_to_direct_markdown_helpers():
    assert md.markdown_link_to_html("[safe](https://example.com)") == (
        '<a href="https://example.com">safe</a>'
    )
    assert md.markdown_link_to_html("[mail](mailto:a@example.com)") == (
        '<a href="mailto:a@example.com">mail</a>'
    )
    assert md.markdown_link_to_html("[rel](docs/page.html)") == (
        '<a href="docs/page.html">rel</a>'
    )
    assert md.markdown_link_to_html("[bad](javascript:evil)") == "bad"
    assert md.markdown_link_to_html("[bad](java\x00script:evil)") == "bad"

    assert md.markdown_image_to_html("![safe](/img.png)") == (
        '<img src="/img.png" alt="safe" />'
    )
    assert md.markdown_image_to_html("![bad](data:text/html,boom)") == "bad"


def test_shared_url_policy_applies_to_markdown_to_html():
    html = md.markdown_to_html(
        "[safe](https://example.com) [bad](javascript:evil) "
        "![badimg](data:text/html,boom)"
    )

    assert '<a href="https://example.com">safe</a>' in html
    assert 'href="javascript:' not in html
    assert 'src="data:' not in html
    assert "bad" in html
    assert "badimg" in html


def test_dom_rejected_urls_degrade_without_empty_link_or_image():
    html = (
        '<a href="javascript:evil">click</a>'
        '<img src="data:text/html,boom" alt="picture">'
    )
    tree = md.parse_html_dom(html)

    assert md.dom_to_html(tree) == "clickpicture"
    back = md.dom_to_markdown(tree)
    assert "[click]()" not in back
    assert "click" in back
    assert "picture" in back


def test_host_port_references_are_normalized_not_rejected():
    assert md.markdown_link_to_html("[local](example.com:8080/path)") == (
        '<a href="//example.com:8080/path">local</a>'
    )
    assert md.markdown_link_to_html("[localhost](localhost:3000/app)") == (
        '<a href="//localhost:3000/app">localhost</a>'
    )
    assert md.markdown_link_to_html("[ipv4](127.0.0.1:8000/x)") == (
        '<a href="//127.0.0.1:8000/x">ipv4</a>'
    )
    assert md.markdown_link_to_html("[ipv6]([::1]:8000/x)") == (
        '<a href="//[::1]:8000/x">ipv6</a>'
    )


def test_host_port_normalization_does_not_open_custom_schemes():
    assert md.markdown_link_to_html("[custom](foo:123/path)") == "custom"
    assert md.markdown_link_to_html("[custom](javascript:123/path)") == "custom"
    assert md.markdown_link_to_html("[badport](example.com:70000/path)") == "badport"


def test_dom_host_port_reference_uses_network_path_form():
    tree = md.parse_html_dom('<a href="example.com:8080/path">local</a>')
    assert md.dom_to_html(tree) == '<a href="//example.com:8080/path">local</a>'


def test_find_html_text_round_trips_unicode_and_entities():
    source = "日本語 & < > \" \' 😀"
    escaped = md.html_module.escape(source, quote=True)
    html = '<p class="lead" data-testid="diagnostic" title="extra">' + escaped + "<strong> nested</strong></p>"
    assert md.find_html_text(html, tag="p", attrs={"data-testid": "diagnostic"}) == source + " nested"


def test_find_html_text_is_attribute_order_independent_and_missing_is_none():
    first = '<p id="x" data-testid="diagnostic">成功 &amp; OK</p>'
    second = '<p data-extra="1" data-testid="diagnostic" id="x">成功 &amp; OK</p>'
    filters = {"id": "x", "data-testid": "diagnostic"}
    assert md.find_html_text(first, tag="P", attrs=filters) == "成功 & OK"
    assert md.find_html_text(second, tag="p", attrs=filters) == "成功 & OK"
    assert md.find_html_text(second, tag="section", attrs=filters) is None


def test_html_text_content_uses_existing_dom_drop_rules():
    root = md.parse_html_dom("<p>Hello <em>世界</em><script>secret</script> 😀</p>")
    assert md.html_text_content(root) == "Hello 世界 😀"


def test_find_html_text_rejects_filters_removed_by_sanitizer():
    import pytest

    with pytest.raises(ValueError, match="unsupported HTML tag filter"):
        md.find_html_text('<span data-testid="x">text</span>', tag="span", attrs={"data-testid": "x"})
    with pytest.raises(ValueError, match="unsupported HTML attribute filter"):
        md.find_html_text('<p role="alert">text</p>', tag="p", attrs={"role": "alert"})


def test_find_html_text_exact_match_and_textcontent_semantics():
    html = '<div><p class="lead extra">a<br>b</p><p>c</p></div>'
    assert md.find_html_text(html, tag="p", attrs={"class": "lead"}) is None
    assert md.find_html_text(html, tag="p", attrs={"class": "lead extra"}) == "ab"


def test_find_html_text_rejects_non_checkbox_input_attribute_filters():
    import pytest

    with pytest.raises(ValueError, match="input require type=checkbox"):
        md.find_html_text('<input type="text" id="x">', tag="input", attrs={"id": "x"})
    assert md.find_html_text(
        '<input type="checkbox" id="x">',
        tag="input",
        attrs={"type": "checkbox", "id": "x"},
    ) == ""


def test_find_html_text_input_filter_keys_are_case_insensitive():
    assert md.find_html_text(
        '<input type="checkbox" id="x">',
        tag="INPUT",
        attrs={"TYPE": "checkbox", "ID": "x"},
    ) == ""


def test_find_html_text_reports_unsupported_input_attribute_first():
    import pytest

    with pytest.raises(ValueError, match="unsupported HTML attribute filter.*role"):
        md.find_html_text(
            '<input type="text" role="alert">',
            tag="input",
            attrs={"role": "alert"},
        )


# ═══ · malformed html recovery ═══════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

AUDIT_SCRIPT = ROOT / "scripts" / "converter_contract_audit.py"


def _load_audit():
    spec = importlib.util.spec_from_file_location("converter_contract_audit", AUDIT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_malformed_ancestor_close_balances_strong_like_dom_path() -> None:
    html = "<div><p>hello<strong> world</div>"

    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == "hello** world**\n"
    assert legacy == dom


def test_malformed_ancestor_close_balances_nested_inline_delimiters() -> None:
    html = "<div><p><strong>bold <em>and italic</div>"

    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == "**bold *and italic***\n"
    assert legacy == dom


def test_malformed_ancestor_close_balances_inline_code() -> None:
    html = "<div><p>use <code>x = 1</div>"

    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == "use `x = 1`\n"
    assert legacy == dom


def test_orphan_endtag_does_not_invent_markup() -> None:
    assert md.html_to_markdown("<p>hello</strong></p>") == "hello\n"


def test_malformed_case_is_no_longer_a_converter_audit_divergence() -> None:
    audit = _load_audit()
    report = audit.collect_report()

    assert "html:malformed" not in report["divergent_case_ids"]


# ═══ · html code newlines ════════════════════════════════════════════════════════════════════════════════
# Compare original code text, not merely stable Markdown after conversion.

def code_text(source):
    root = md.parse_html_dom(source)

    def texts(node):
        if node.kind == 'text':
            return node.text
        return ''.join(texts(child) for child in node.children or [])

    def find(node):
        if node.tag == 'code':
            return texts(node)
        for child in node.children or []:
            result = find(child)
            if result is not None:
                return result
        return None

    return find(root)


@pytest.mark.parametrize('code', [
    'ffmpeg -i input.avi output.mp4\n',
    'def main():\n    return "#CSS & HTML"\n',
    'first\n\n\n\nlast\n',
    'first\n\n\n',
    '\n\nfirst\n',
    '日本語\t= 1  \n\treturn 日本語  \n',
])
@pytest.mark.parametrize('surround', [False, True])
def test_html_code_preserves_literal_newlines_and_spaces(code, surround):
    source = '<pre><code>' + html.escape(code) + '</code></pre>'
    if surround:
        source = '<p>before</p>' + source + '<p>after</p>'
    converted = md.html_to_markdown(source)
    restored = md.markdown_to_html(converted)
    assert code_text(restored) == code
    assert md.html_to_markdown(restored) == converted


def test_highlight_spans_do_not_add_a_code_line():
    source = '<pre><code>deno <span class="token function">install</span>\n</code></pre>'
    assert code_text(md.markdown_to_html(md.html_to_markdown(source))) == 'deno install\n'


def test_source_without_terminal_lf_retains_existing_fenced_code_normalization():
    # Markdown fenced code is line-oriented: exact no-LF HTML is not promised.
    # This is a limitation, not evidence of a lossless round trip.
    source = '<pre><code>no newline</code></pre>'
    assert code_text(md.markdown_to_html(md.html_to_markdown(source))) == 'no newline\n'


@pytest.mark.parametrize('code', [
    'a\n\n\n\n', '\n\nfirst\n', '日本語\t= 1  \n\treturn 日本語  \n',
    ':::details not a container\n:::\n<script>literal</script>\n',
])
def test_code_inside_details_roundtrips_without_losing_structure(code):
    source = '<details><summary>Code</summary><p>before</p><pre><code>' + html.escape(code) + '</code></pre><p>after</p></details>'
    converted = md.html_to_markdown(source)
    restored = md.markdown_to_html(converted)
    assert '<details>\n<summary>Code</summary>' in restored
    assert '<p>before</p>\n<pre><code>' in restored
    assert '</code></pre>\n<p>after</p>\n</details>' in restored
    assert code_text(restored) == code
    assert '<script>' not in restored
    assert md.html_to_markdown(restored) == converted


# ═══ · data uri boundaries ═══════════════════════════════════════════════════════════════════════════════

def test_data_uri_preserves_payload_terminal_punctuation():
    cases = [
        ("data:text/plain,Hello!", "data:text/plain,Hello!"),
        ("data:text/plain,Hello?", "data:text/plain,Hello?"),
        ("data:text/plain,hello.", "data:text/plain,hello."),
        ("data:,", "data:,"),
        ("data:text/plain,!!!", "data:text/plain,!!!"),
        ("<data:text/plain,Hello!>", "data:text/plain,Hello!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected


def test_data_uri_drops_only_unmatched_markdown_closing_parenthesis():
    result = md.extract_data_uris("(data:text/plain,hello)")
    assert result[0]["uri"] == "data:text/plain,hello"


def test_data_uri_drops_unmatched_paren_followed_by_sentence_punctuation():
    """The common prose case: a data URI in parens at the end of a
    sentence, e.g. "See (data:...,hello)." -- both the unmatched ``)``
    and the trailing "." that was only wrapping it must go, while a
    genuinely balanced payload paren (no imbalance) stays untouched."""
    result = md.extract_data_uris("See (data:text/plain,hello).")
    assert result[0]["uri"] == "data:text/plain,hello"

    balanced = md.extract_data_uris("data:text/plain,a(b)c")
    assert balanced[0]["uri"] == "data:text/plain,a(b)c"


def test_data_uri_keeps_ordinary_payload_bytes_around_unmatched_parens():
    """An imbalanced paren count must not license eating arbitrary trailing
    payload characters -- only ")" and prose punctuation are delimiters;
    anything else stops the strip immediately, even while still imbalanced."""
    cases = [
        ("data:text/plain,a)b", "data:text/plain,a)b"),
        ("data:text/plain,x)y)z", "data:text/plain,x)y)z"),
        ("data:text/plain,payload_with)inside)", "data:text/plain,payload_with)inside"),
        ("data:text/plain,))extra", "data:text/plain,))extra"),
        ("data:text/plain,)hello", "data:text/plain,)hello"),
        ("data:text/plain,a)b)c", "data:text/plain,a)b)c"),
        # A trailing run that contains no ")" at all is never a delimiter
        # run, even if it starts right after an unmatched ")" further back.
        ("data:text/plain,hello)world!", "data:text/plain,hello)world!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_keeps_payload_punctuation_immediately_before_the_paren():
    """Punctuation that sits *before* an unmatched ")" is payload, not a
    delimiter -- only punctuation trailing *after* the ")" (the prose that
    was wrapping it) gets stripped along with it."""
    cases = [
        ("See (data:text/plain,Hello!).", "data:text/plain,Hello!"),
        ("See (data:text/plain,Hello?).", "data:text/plain,Hello?"),
        ("See (data:text/plain,done.).", "data:text/plain,done."),
        ("(data:text/plain,Hello!)", "data:text/plain,Hello!"),
        ("![x](data:text/plain,Hello!)", "data:text/plain,Hello!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_trailing_backslash_is_kept():
    """rstrip() here only removes surrounding quote/angle delimiters, same
    as the rest of this module -- a payload ending in "\\" is not one."""
    result = md.extract_data_uris("data:text/plain,ends\\")
    assert result[0]["uri"] == "data:text/plain,ends\\"


def test_data_uri_strips_all_excess_closers_from_stacked_wrappers():
    """A prose paren wrapping a Markdown link/image leaves 2+ unmatched
    ")" at the end -- the cut must remove all of the excess, not just the
    single rightmost one, while still keeping a genuinely balanced payload
    paren that sits inside that excess."""
    cases = [
        ("(see ![x](data:text/plain,hello))", "data:text/plain,hello"),
        ("(see ![x](data:text/plain,a(b)))", "data:text/plain,a(b)"),
        ("((data:text/plain,hello))", "data:text/plain,hello"),
        ("![x](data:text/plain,hello))", "data:text/plain,hello"),
        ("See (data:text/plain,a(b))).", "data:text/plain,a(b)"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_strips_angle_bracket_exposed_by_paren_removal():
    """Removing a wrapping ")" can expose a "<...>"-style delimiter that
    was hidden behind it -- e.g. "(<data:...,x>)" -- and that exposed ">"
    must also be dropped, not left dangling on the observed URI."""
    cases = [
        ("See (<data:text/plain,Hello!>).", "data:text/plain,Hello!"),
        ("(<data:text/plain,Hello!>)", "data:text/plain,Hello!"),
    ]
    for source, expected in cases:
        result = md.extract_data_uris(source)
        assert result[0]["uri"] == expected, source


def test_data_uri_rejects_prefixed_false_positives():
    assert md.extract_data_uris("notdata:text/plain,x") == []
    assert md.extract_data_uris("foo_data:text/plain,x") == []


def test_data_uri_keeps_base64_form():
    assert md.extract_data_uris("data:image/png;base64,AAAA") == [{
        "uri": "data:image/png;base64,AAAA",
        "media_type": "image/png",
        "metadata": "image/png;base64",
    }]


def test_data_uri_rejects_metadata_like_non_media_type_headers():
    assert md.extract_data_uris("data:metadata:record,hello") == []


def test_data_uri_uses_text_plain_for_an_omitted_media_type():
    assert md.extract_data_uris("data:,text") == [{
        "uri": "data:,text",
        "media_type": "text/plain",
        "metadata": "",
    }]


# ═══ · data uris ═════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
import markdown as md

def test_data_uri_is_observed_without_decoding_or_network() -> None:
    uri = "data:image/png;base64,iVBORw0KGgo="
    assert md.extract_data_uris(f"![x]({uri})") == [{"uri": uri, "media_type": "image/png", "metadata": "image/png;base64"}]


# ═══ · live extraction ═══════════════════════════════════════════════════════════════════════════════════
# Extractors ignore Markdown shown inside code or HTML comments; angle autolinks count.

DOC = """# Title

```python
# not a heading
print("[x](https://code.example) ![i](code.png)")
```

Use `[inline](https://inline.example)` or visit <https://auto.example>.
A [`code` label](https://real.example) stays.

<!--
## Template heading
[template](https://template.example)
-->

~~~
## also code
~~~
"""


def test_extract_sections_skips_fenced_code_and_comments():
    assert md.extract_sections(DOC) == [{"level": 1, "title": "Title"}]


def test_extract_links_skips_code_and_comments_and_reports_autolinks():
    links = md.extract_links(DOC)
    assert [(link["style"], link["url"]) for link in links] == [
        ("inline", "https://real.example"), ("autolink", "https://auto.example")]
    assert links[0]["text"] == "`code` label"


def test_extract_images_skips_code():
    assert md.extract_images(DOC) == []
    assert [i["url"] for i in md.extract_images("![a](a.png)\n`![b](b.png)`\n")] == ["a.png"]


def test_reference_definitions_inside_code_are_ignored():
    text = "[r][key]\n\n[key]: https://real.example\n\n```\n[key]: https://code.example\n```\n"
    assert [link["url"] for link in md.extract_links(text)] == ["https://real.example"]


def test_crlf_input_keeps_spans():
    assert md.extract_links("```\r\n[x](y)\r\n```\r\n[a](b)\r\n") [0]["url"] == "b"


def test_display_width_counts_emoji_sequences_once():
    assert [md._display_width(t) for t in ("👍🏽", "👨‍👩‍👧", "❤️", "​", "x‍y", "日本")] == [2, 2, 2, 0, 2, 4]


def test_unterminated_html_comment_hides_headings_and_links_through_eof():
    text = (
        "# Visible\n\n"
        "[keep](https://keep.example)\n\n"
        "![keep](keep.png)\n\n"
        "<!--\n"
        "# hidden\n"
        "[hidden](https://example.invalid)\n"
        "![hidden](hidden.png)\n"
    )
    assert md.extract_sections(text) == [{"level": 1, "title": "Visible"}]
    assert [link["url"] for link in md.extract_links(text)] == ["https://keep.example"]
    assert [image["url"] for image in md.extract_images(text)] == ["keep.png"]


def test_closed_html_comment_does_not_hide_what_follows():
    text = "<!--\n# hidden\n[hidden](https://example.invalid)\n-->\n# After\n[a](https://after.example)\n"
    assert md.extract_sections(text) == [{"level": 1, "title": "After"}]
    assert [link["url"] for link in md.extract_links(text)] == ["https://after.example"]


def test_comment_opener_inside_a_fence_does_not_eat_the_rest():
    text = "```\n<!--\n```\n# After\n[a](https://after.example)\n"
    assert md.extract_sections(text) == [{"level": 1, "title": "After"}]
    assert [link["url"] for link in md.extract_links(text)] == ["https://after.example"]


@pytest.mark.parametrize("comment", [
    "<!--\n```\n-->\n",
    "<!--\n~~~\n-->\n",
    "<!-- ` --> `\n",
    "<!--\n`-->`\n",
])
def test_code_markers_inside_comments_do_not_hide_following_content(comment):
    text = comment + "# After\n[a](https://after.example)\n![a](after.png)\n"
    assert md.extract_sections(text) == [{"level": 1, "title": "After"}]
    assert [link["url"] for link in md.extract_links(text)] == ["https://after.example"]
    assert [image["url"] for image in md.extract_images(text)] == ["after.png"]


def test_comment_opener_inside_inline_code_does_not_hide_following_content():
    text = "`<!--`\n# After\n[a](https://after.example)\n"
    assert md.extract_sections(text) == [{"level": 1, "title": "After"}]
    assert [link["url"] for link in md.extract_links(text)] == ["https://after.example"]


def test_visible_tail_does_not_reactivate_a_commented_heading_marker():
    text = "<!--\n# hidden --> tail\n# After\n"
    assert md.extract_sections(text) == [{"level": 1, "title": "After"}]


# ═══ · tohoho whitespace stability ═══════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

TOHOHO = ROOT / "fixtures" / "benchmark" / "tohoho_web_home.html"


def _first_diff(left: str, right: str) -> tuple[int, str, str]:
    index = next(
        (i for i, (a, b) in enumerate(zip(left, right)) if a != b),
        min(len(left), len(right)),
    )
    lo = max(0, index - 100)
    hi = index + 100
    return index, repr(left[lo:hi]), repr(right[lo:hi])


def test_tohoho_markdown_is_stable_after_html_round_trip() -> None:
    html = TOHOHO.read_text(encoding="utf-8")
    first = md.html_to_markdown(html)
    second = md.html_to_markdown(md.markdown_to_html(first))

    assert first == second, _first_diff(first, second)


def test_tohoho_dom_markdown_is_stable_after_dom_round_trip() -> None:
    html = TOHOHO.read_text(encoding="utf-8")
    first = md.dom_to_markdown(md.parse_html_dom(html))
    second = md.dom_to_markdown(md.markdown_to_dom(first))

    assert first == second, _first_diff(first, second)


def test_html_block_boundaries_drop_formatting_whitespace() -> None:
    html = "prefix   <h2>Heading </h2><ul><li>one </li><li>two</li></ul>"
    markdown = md.html_to_markdown(html)

    assert markdown == "prefix\n\n## Heading\n\n- one\n- two\n"


def test_markdown_hard_break_survives_html_round_trip() -> None:
    source = "first line  \nsecond line\n"

    html = md.markdown_to_html(source)

    assert "<br />" in html
    assert md.html_to_markdown(html) == source


def test_source_text_ending_like_blockquote_prefix_is_still_trimmed() -> None:
    html = "<span>literal &gt; </span><h2>Heading</h2>"

    assert md.html_to_markdown(html) == "literal >\n\n## Heading\n"


def test_nested_list_marker_space_is_preserved_by_parser_provenance() -> None:
    html = "<ul><li><ol><li>nested</li></ol></li></ul>"

    assert md.html_to_markdown(html) == "- \n  1. nested\n"


def test_blockquote_continuation_prefix_survives_empty_paragraph_before_list() -> None:
    html = "<blockquote><p>a</p><p></p><ul><li>x</li></ul></blockquote>"

    markdown = md.html_to_markdown(html)

    assert ">\n> " in markdown


# ═══ · context helpers ═══════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


SAMPLE = (
    "# Intro\n"
    "ordinary prose\n"
    "## Target\n"
    "target body\n"
    "### Child\n"
    "child body\n"
    "## Next\n"
    "next body\n"
)


def test_extract_section_respects_heading_boundaries() -> None:
    assert md.extract_section(SAMPLE, "Target") == (
        "## Target\n"
        "target body\n"
        "### Child\n"
        "child body\n"
    )
    assert md.extract_section(SAMPLE, "intro", level=1) == (
        "# Intro\n"
        "ordinary prose\n"
        "## Target\n"
        "target body\n"
        "### Child\n"
        "child body\n"
        "## Next\n"
        "next body\n"
    )
    assert md.extract_section(SAMPLE, "tar", partial=True) == (
        "## Target\n"
        "target body\n"
        "### Child\n"
        "child body\n"
    )
    assert md.extract_section(SAMPLE, "missing") == ""


def test_strip_prose_keep_structure_preserves_fences() -> None:
    content = (
        "ordinary prose\n"
        "# Heading\n"
        "another paragraph\n"
        "- item\n"
        "> quote\n"
        "```python\n"
        "ordinary prose inside code\n"
        "```\n"
        "trailer prose\n"
    )
    assert md.strip_prose_keep_structure(content) == (
        "# Heading\n"
        "- item\n"
        "> quote\n"
        "```python\n"
        "ordinary prose inside code\n"
        "```\n"
    )


def test_minify_markdown_is_physical_only() -> None:
    content = "  # Title  \n\n\n<!-- generated -->\n\nbody\n"
    assert md.minify_markdown(content) == "# Title  \n\nbody"
    assert md.minify_markdown(content, strip_html=False) == (
        "# Title  \n\n<!-- generated -->\n\nbody"
    )


def test_safe_truncate_closes_fence_within_limit() -> None:
    content = "before\n```python\nalpha\nbeta\n```\nafter\n"
    result = md.safe_truncate(content, 24)
    assert len(result) <= 24
    assert result.endswith("```")
    blocks = md.extract_code_blocks(result)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"


def test_safe_truncate_short_and_invalid_limits() -> None:
    content = "short\n"
    assert md.safe_truncate(content, len(content)) == content
    with pytest.raises(ValueError):
        md.safe_truncate(content, -1)


def test_context_helpers_are_public() -> None:
    for name in (
        "extract_section",
        "strip_prose_keep_structure",
        "minify_markdown",
        "safe_truncate",
    ):
        assert name in md.__all__
        assert hasattr(md, name)


# ═══ · reversible composition ════════════════════════════════════════════════════════════════════════════
# Negative-space tests for explicit reversible converter composition.
#
# Positive F/G/H identity cycles are already covered by
# scripts/converter_contract_audit.py and test_converter_contract_audit.py.
# This file intentionally keeps only composition boundaries that should fail or
# remain structurally distinct, avoiding duplicated positive fixtures.

def test_cross_domain_composition_fails_instead_of_coercing():
    if md.toml_reader() is None:
        pytest.skip("TOML reader requires Python 3.11+ or Node with smol-toml")

    # A TOML integer is outside dotenv's flat string-value subset.
    x = "count = 3\n"
    f_x = md.toml_to_markdown(x)

    with pytest.raises(ValueError, match="dotenv values must be strings"):
        md.markdown_to_dotenv(f_x)


def test_ini_and_dotenv_are_not_forced_into_same_shape():
    ini_x = "[section]\nkey=value\n"
    dotenv_x = "KEY=value\n"

    ini_md = md.ini_to_markdown(ini_x)
    dotenv_md = md.dotenv_to_markdown(dotenv_x)

    assert md.markdown_to_structured(ini_md) == {"section": {"key": "value"}}
    assert md.markdown_to_structured(dotenv_md) == {"KEY": "value"}
    assert md.markdown_to_structured(ini_md) != md.markdown_to_structured(dotenv_md)


# ═══ · fixtures and serialize ════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures"


def _load_provenance() -> dict:
    return yaml.safe_load((FIXTURES / "provenance.yaml").read_text(encoding="utf-8"))


def test_real_world_fixtures_against_provenance() -> None:
    data = _load_provenance()
    for item in data["fixtures"]:
        content = (FIXTURES / item["path"]).read_text(encoding="utf-8")
        inv = md.inventory(content)
        expect = item["expect"]
        assert inv["heading_count"] >= expect["min_headings"], item["id"]
        assert inv["image_count"] >= expect["min_images"], item["id"]
        assert inv["link_count"] >= expect["min_links"], item["id"]
        assert inv["code_block_count"] >= expect["min_code_blocks"], item["id"]
        if expect.get("has_horizontal_rule"):
            assert inv["horizontal_rule_count"] >= 1, item["id"]
        if expect.get("has_reference_links"):
            assert any(link.get("style") == "reference" for link in inv["links"]), item["id"]
        for tag in expect.get("has_raw_html_tags", []):
            assert any(h["tag"] == tag for h in inv["raw_html"]), (item["id"], tag)


def test_unsupported_constructs_are_documented() -> None:
    data = _load_provenance()
    notes = {row["name"]: row["note"] for row in data["unsupported_examples"]}
    assert "bare_url_autolink" in notes
    assert "kramdown_extension_and_toc" in notes
    assert "liquid_and_front_matter" in notes
    assert "footnote" not in notes
    bare = next(row for row in data["unsupported_examples"] if row["name"] == "bare_url_autolink")
    bare_html = md.markdown_to_html(bare["markdown"])
    assert "<a " not in bare_html
    assert "https://example.com" in bare_html


def test_footnote_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "footnote")
    html = md.markdown_to_html(example["markdown"])
    assert '<sup class="footnote-ref">' in html
    assert "the note" in html
    assert "footnotes" in html


def test_details_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "details")
    html = md.markdown_to_html(example["markdown"])
    assert "<details>" in html
    assert "<summary>Summary</summary>" in html
    assert "Hidden body" in html


def test_task_list_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "task_list")
    html = md.markdown_to_html(example["markdown"])
    assert "<input" in html
    assert "disabled" in html
    assert "todo" in html
    assert "checked" in html


def test_strikethrough_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "strikethrough")
    html = md.markdown_to_html(example["markdown"])
    assert "<del>mistake</del>" in html


def test_angle_autolink_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "angle_autolink")
    html = md.markdown_to_html(example["markdown"])
    assert '<a href="https://example.com">https://example.com</a>' in html


def test_kramdown_ial_example_converts() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "kramdown_ial")
    kd = md.markdown_to_kramdown(example["markdown"])
    assert "{: #intro .hero}" in kd
    assert md.kramdown_to_markdown(kd).startswith("# Title")


def test_unsupported_kramdown_and_liquid_examples_stay_literal() -> None:
    data = _load_provenance()
    for name in ("kramdown_extension_and_toc", "liquid_and_front_matter"):
        row = next(item for item in data["unsupported_examples"] if item["name"] == name)
        src = row["markdown"]
        assert md.markdown_to_kramdown(src) == src
        assert md.kramdown_to_markdown(src) == src


def test_gfm_table_example_now_renders() -> None:
    data = _load_provenance()
    example = next(row for row in data["supported_examples"] if row["name"] == "gfm_table")
    html = md.markdown_to_html(example["markdown"])
    assert "<table>" in html
    assert "<th>a</th>" in html
    assert "<td>1</td>" in html


def test_json_fixture_roundtrip_helpers() -> None:
    payload = json.loads((FIXTURES / "roundtrip.json").read_text(encoding="utf-8"))
    rt = payload["roundtrip"]
    assert md.html_image_to_markdown(rt["html_image"]) == rt["markdown_image"]
    assert md.html_link_to_markdown(rt["html_link"]) == rt["markdown_link"]
    inv_keys = payload["sample_inventory_keys"]
    sample = (FIXTURES / "kubernetes_readme_snippet.md").read_text(encoding="utf-8")
    inv = md.inventory(sample)
    for key in inv_keys:
        assert key in inv


def test_yaml_json_toml_serialize_inventory(tmp_path: Path) -> None:
    content = (FIXTURES / "vscode_readme_snippet.md").read_text(encoding="utf-8")
    inv = md.inventory(content)
    slim = {
        "heading_count": inv["heading_count"],
        "link_count": inv["link_count"],
        "image_count": inv["image_count"],
        "urls": inv["urls"],
    }

    yaml_path = tmp_path / "inv.yaml"
    json_path = tmp_path / "inv.json"
    toml_path = tmp_path / "inv.toml"

    yaml_path.write_text(yaml.safe_dump(slim, sort_keys=True), encoding="utf-8")
    json_path.write_text(json.dumps(slim, indent=2), encoding="utf-8")

    # TOML write via stdlib is awkward for nested lists; keep a tiny document.
    toml_path.write_text(
        "[counts]\n"
        f"heading_count = {slim['heading_count']}\n"
        f"link_count = {slim['link_count']}\n"
        f"image_count = {slim['image_count']}\n",
        encoding="utf-8",
    )

    assert yaml.safe_load(yaml_path.read_text(encoding="utf-8"))["heading_count"] == slim[
        "heading_count"
    ]
    assert json.loads(json_path.read_text(encoding="utf-8"))["link_count"] == slim["link_count"]

    tomllib = pytest.importorskip("tomllib")
    loaded = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    assert loaded["counts"]["image_count"] == slim["image_count"]

    meta = tomllib.loads((FIXTURES / "meta.toml").read_text(encoding="utf-8"))
    assert meta["meta"]["name"] == "markdown-single-file"
    assert meta["expect"]["heading_title"] == "Hello"


# ═══ · mirror js ═════════════════════════════════════════════════════════════════════════════════════════
# Mirror tests: markdown.py must agree with independent JS implementations.
#
# markdown-it (CommonMark) and marked (GFM) render every Markdown file in this
# repository, linkedom reads the HTML; string-width measures display widths. No
# browser is involved. Neither side is the oracle: a disagreement is a lead.
# Known dialect difference: marked autolinks bare URLs, markdown.py and CommonMark
# do not, so links are compared with markdown-it only.
#
# Needs ``npm ci --prefix tests/mirror`` (CI does this); skipped without it.

MIRROR = ROOT / "tests" / "mirror"
MIRROR_JS_MARK = pytest.mark.skipif(
    not (MIRROR / "node_modules").is_dir() or shutil.which("node") is None,
    reason="run `npm ci --prefix tests/mirror` to enable the JS mirror",
)

WIDTHS = ["abc", "日本語", "ｶﾀｶﾅ", "ＡＢＣ", "é", "한국어", "中文，標點", "±§", "😀", "👍🏽",
          "👨‍👩‍👧", "🇯🇵", "❤️", "☺", "©", "→", "…", "　", "áb", "​", "ー",
          "🏝️", "🗺", "👩🏽‍💻", "x‍y", "🏳️‍🌈", "a︎", "表|示"]


def _plain(text: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(re.sub(r"[`*_]", "", text).split())


def ours(text: str) -> dict:
    return {
        "headings": [[s["level"], s["title"]] for s in md.extract_sections(text)],
        "links": [link["url"] for link in md.extract_links(text)],
        "images": [[image["url"], image["alt"]] for image in md.extract_images(text)],
        "code": [[block["language"], block["code"]] for block in md.extract_code_blocks(text)],
    }


def normalized(key: str, items: list) -> collections.Counter:
    if key == "headings":
        return collections.Counter((int(level), _plain(title)) for level, title in items)
    if key == "images":
        return collections.Counter((src, _plain(alt)) for src, alt in items)
    if key == "code":
        return collections.Counter((lang, text.rstrip("\n")) for lang, text in items)
    return collections.Counter(items)


@pytest.fixture(scope="module")
def readers():
    # This repository's own documents only: CI checks out helper repos (.vendor-sync-tools) inside it.
    skip = {"node_modules", "build"}
    files = sorted(p for p in ROOT.rglob("*.md")
                   if not any(part.startswith(".") or part in skip for part in p.relative_to(ROOT).parts))
    texts = [p.read_text(encoding="utf-8") for p in files]
    done = subprocess.run(["node", str(MIRROR / "facts.mjs")], input=json.dumps({"markdown": texts, "width": WIDTHS}),
                          capture_output=True, text=True, check=True, timeout=120)
    return files, texts, json.loads(done.stdout)


@MIRROR_JS_MARK
@pytest.mark.parametrize("key,reader", [("headings", "markdown-it"), ("headings", "marked"),
                                        ("links", "markdown-it"), ("images", "markdown-it"),
                                        ("images", "marked"), ("code", "markdown-it"), ("code", "marked")])
def test_markdown_facts_agree_with_js_renderers(readers, key, reader):
    files, texts, facts = readers
    mismatches = []
    for path, text, theirs in zip(files, texts, facts[reader]):
        a, b = normalized(key, ours(text)[key]), normalized(key, theirs[key])
        if a != b:
            mismatches.append(f"{path.relative_to(ROOT)}: only markdown.py {list((a - b).elements())[:2]}"
                              f" only {reader} {list((b - a).elements())[:2]}")
    assert not mismatches, "\n".join(mismatches)


@MIRROR_JS_MARK
def test_display_width_agrees_with_string_width(readers):
    expected = readers[2]["string-width"]
    actual = [md._display_width(text) for text in WIDTHS]
    assert [(t, a, e) for t, a, e in zip(WIDTHS, actual, expected) if a != e] == []


# An HTML comment with no closing "-->" runs to EOF for markdown-it and marked.
UNTERMINATED_COMMENT = """# Visible

[keep](https://keep.example)

![keep](keep.png)

<!--
# hidden
[hidden](https://example.invalid)
![hidden](hidden.png)
"""


@MIRROR_JS_MARK
def test_unterminated_html_comment_agrees_with_js_renderers():
    done = subprocess.run(
        ["node", str(MIRROR / "facts.mjs")],
        input=json.dumps({"markdown": [UNTERMINATED_COMMENT], "width": []}),
        capture_output=True, text=True, check=True, timeout=120,
    )
    facts = json.loads(done.stdout)
    py = ours(UNTERMINATED_COMMENT)
    assert py["headings"] == [[1, "Visible"]]
    assert py["links"] == ["https://keep.example"]
    assert py["images"] == [["keep.png", "keep"]]
    for reader in ("markdown-it", "marked"):
        theirs = facts[reader][0]
        assert normalized("headings", py["headings"]) == normalized("headings", theirs["headings"])
        assert normalized("images", py["images"]) == normalized("images", theirs["images"])
        assert "https://example.invalid" not in theirs["links"]
        assert "hidden.png" not in [src for src, _alt in theirs["images"]]
    assert normalized("links", py["links"]) == normalized("links", facts["markdown-it"][0]["links"])


@MIRROR_JS_MARK
def test_comment_code_boundaries_agree_with_js_renderers():
    comments = ["<!--\n```\n-->\n", "<!--\n~~~\n-->\n", "<!-- ` --> `\n",
                "<!--\n`-->`\n", "`<!--`\n", "```\n<!--\n```\n", "<!--\n# hidden --> tail\n"]
    texts = [comment + "# After\n[a](https://after.example)\n![a](after.png)\n" for comment in comments]
    done = subprocess.run(
        ["node", str(MIRROR / "facts.mjs")],
        input=json.dumps({"markdown": texts, "width": []}),
        capture_output=True, text=True, check=True, timeout=120,
    )
    facts = json.loads(done.stdout)
    for reader in ("markdown-it", "marked"):
        for text, theirs in zip(texts, facts[reader]):
            py = ours(text)
            for key in ("headings", "links", "images"):
                assert normalized(key, py[key]) == normalized(key, theirs[key]), (reader, key, text)
