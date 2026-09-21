import markdown as md


PARITY_CASES = {
    "heading_and_paragraph": "<h1>Title</h1><p>Hello <strong>world</strong>.</p>",
    "links_and_images": (
        '<p><a href="https://example.com">docs</a> '
        '<img src="/img.png" alt="pic"></p>'
    ),
    "mixed_lists": "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>",
    "table": (
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    ),
    "task": '<ul><li><input type="checkbox" checked disabled> done</li></ul>',
    "unicode": "<p>日本語 <strong>世界</strong> café</p>",
    "unsafe_link_sanitization": '<p><a href="javascript:alert(1)">click</a></p>',
}


KNOWN_DOM_LEGACY_GAPS = {}


def test_public_html_to_markdown_is_a_compatibility_wrapper():
    for html in [*PARITY_CASES.values(), *KNOWN_DOM_LEGACY_GAPS.values()]:
        assert md.html_to_markdown(html) == md._html_to_markdown_impl(html)


def test_dom_and_legacy_paths_match_for_supported_parity_cases():
    for name, html in PARITY_CASES.items():
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert dom == legacy, name


def test_known_dom_legacy_gaps_are_explicit_and_stable():
    observed = {}
    for name, html in KNOWN_DOM_LEGACY_GAPS.items():
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        if legacy != dom:
            observed[name] = (legacy, dom)

    assert set(observed) == set(KNOWN_DOM_LEGACY_GAPS)


def test_dom_path_does_not_call_public_html_to_markdown(monkeypatch):
    def fail_public_wrapper(_html: str) -> str:
        raise AssertionError("dom_to_markdown must not call public html_to_markdown")

    monkeypatch.setattr(md, "html_to_markdown", fail_public_wrapper)

    assert md.dom_to_markdown(md.parse_html_dom("<p>Hello</p>")) == "Hello\n"

    details = md.dom_to_markdown(
        md.parse_html_dom(
            "<details><summary>More</summary><p>Body <strong>text</strong>.</p></details>"
        )
    )
    assert details.startswith(":::details More\n")
    assert "Body **text**." in details


URL_SAFETY_CASES = [
    ('<a href="javascript:alert(1)">click</a>', "click\n"),
    ('<a href="JavaScript:alert(1)">click</a>', "click\n"),
    ('<a href="javascript\x00:alert(1)">click</a>', "click\n"),
    ('<a href="java\tscript:alert(1)">click</a>', "click\n"),
    ('<a href="java\nscript:alert(1)">click</a>', "click\n"),
    ('<a href="data:text/html,boom">click</a>', "click\n"),
    ('<a href="vbscript:msgbox(1)">click</a>', "click\n"),
    ('<a href="https://example.com/x">click</a>', "[click](https://example.com/x)\n"),
    ('<a href="mailto:test@example.com">mail</a>', "[mail](mailto:test@example.com)\n"),
    ('<a href="../docs/page.html">docs</a>', "[docs](../docs/page.html)\n"),
    ('<a href="example.com:8080/path">host</a>', "[host](//example.com:8080/path)\n"),
    ('<img src="javascript:alert(1)" alt="pic">', "pic\n"),
    ('<img src="data:text/html,boom" alt="pic">', "pic\n"),
    ('<img src="/img.png" alt="pic">', "![pic](/img.png)\n"),
]


def test_legacy_html_url_safety_matches_dom_final_markdown():
    for html, expected in URL_SAFETY_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == expected, html
        assert dom == expected, html


def test_rejected_url_targets_never_emit_empty_markdown_targets():
    samples = [
        '<a href="javascript:alert(1)">click</a>',
        '<img src="javascript:alert(1)" alt="pic">',
    ]
    for html in samples:
        result = md.html_to_markdown(html)
        assert "]()" not in result
        assert "![](" not in result


EMPTY_OUTPUT_CASES = [
    "",
    "   ",
    "<script>alert(1)</script>",
    "<style>body{display:none}</style>",
    '<a href="javascript:x"></a>',
    '<img src="javascript:x" alt="">',
]


def test_empty_html_to_markdown_normalizes_to_empty_string():
    for html in EMPTY_OUTPUT_CASES:
        assert md.html_to_markdown(html) == "", html


def test_empty_output_matches_dom_path():
    for html in EMPTY_OUTPUT_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == dom == "", html


def test_non_empty_html_to_markdown_keeps_single_trailing_newline():
    samples = [
        ("<p>Hello</p>", "Hello\n"),
        ('<a href="https://example.com">x</a>', "[x](https://example.com)\n"),
        ('<img src="/x.png" alt="pic">', "![pic](/x.png)\n"),
    ]
    for html, expected in samples:
        assert md.html_to_markdown(html) == expected


DETAILS_PARITY_CASES = [
    (
        "<details><summary>More</summary><p>Body <em>text</em>.</p></details>",
        ":::details More\nBody *text*.\n:::\n",
    ),
    (
        "<details><p>Body only</p></details>",
        ":::details Details\nBody only\n:::\n",
    ),
    (
        "<details><summary></summary></details>",
        ":::details Details\n:::\n",
    ),
    (
        "<p>Before</p><details><summary>More</summary><p>Body</p></details><p>After</p>",
        "Before\n\n:::details More\nBody\n:::\n\nAfter\n",
    ),
]


def test_details_html_to_markdown_matches_dom_contract():
    for html, expected in DETAILS_PARITY_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == expected, html
        assert dom == expected, html
