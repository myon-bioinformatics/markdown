import markdown as md


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
