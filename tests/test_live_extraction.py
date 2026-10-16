"""Extractors ignore Markdown shown inside code or HTML comments; angle autolinks count."""
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
