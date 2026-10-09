"""Compare original code text, not merely stable Markdown after conversion."""
import html

import pytest

import markdown as md


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
