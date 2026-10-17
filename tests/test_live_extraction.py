"""Extractors ignore Markdown shown inside code or HTML comments; angle autolinks count."""
import pytest

import markdown as md

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
