import pytest

import markdown as md


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
