"""P1 residual audit: fenced/inline-code exclusion + data: URI classification.

extract_links / extract_images / extract_urls / extract_raw_html previously
matched their regexes directly against raw content, so Markdown-about-
Markdown inside a fenced example or `inline code` span was extracted as if
it were real. These contracts pin the fix: every extractor now routes
through the shared ``_mask_code_context`` helper (built from the existing
``_scan_lines`` / ``_mask_inline_code`` scanner primitives), and ``data:``
URLs get a safe, non-decoding classification via ``classify_data_uri``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


# ---------------------------------------------------------------------------
# Fenced code exclusion
# ---------------------------------------------------------------------------

FENCED_SAMPLE = (
    "Real link: [a](https://example.test/a)\n"
    "\n"
    "```markdown\n"
    "Fenced example: [b](https://example.test/b)\n"
    "![alt](https://example.test/img-in-fence.png)\n"
    "<a href=\"https://example.test/html-in-fence\">html</a>\n"
    "<https://example.test/angle-in-fence>\n"
    "\n"
    "```\n"
)


def test_extract_links_ignores_fenced_code() -> None:
    urls = [item["url"] for item in md.extract_links(FENCED_SAMPLE)]
    assert urls == ["https://example.test/a"]


def test_extract_images_ignores_fenced_code() -> None:
    assert md.extract_images(FENCED_SAMPLE) == []


def test_extract_raw_html_ignores_fenced_code() -> None:
    assert md.extract_raw_html(FENCED_SAMPLE) == []


def test_extract_urls_ignores_fenced_code_across_all_sources() -> None:
    assert md.extract_urls(FENCED_SAMPLE) == ["https://example.test/a"]


def test_reference_style_definition_inside_fence_is_not_resolved() -> None:
    content = (
        "See [ref][id].\n"
        "\n"
        "```text\n"
        "[id]: https://example.test/should-not-resolve\n"
        "```\n"
    )
    links = md.extract_links(content)
    assert len(links) == 1
    assert links[0]["url"] == ""


# ---------------------------------------------------------------------------
# Inline code exclusion
# ---------------------------------------------------------------------------

INLINE_CODE_SAMPLE = (
    "Real: [a](https://example.test/a) and "
    "`[hidden](https://example.test/hidden)` and "
    "`<https://example.test/angle-hidden>` and "
    "`<img src=\"https://example.test/hidden.png\">`."
)


def test_extract_links_ignores_inline_code() -> None:
    urls = [item["url"] for item in md.extract_links(INLINE_CODE_SAMPLE)]
    assert urls == ["https://example.test/a"]


def test_extract_urls_ignores_inline_code() -> None:
    assert md.extract_urls(INLINE_CODE_SAMPLE) == ["https://example.test/a"]


def test_extract_raw_html_ignores_inline_code() -> None:
    content = 'Real: <b>bold</b> and `<i>hidden</i>`.'
    tags = [item["snippet"] for item in md.extract_raw_html(content)]
    assert tags == ["<b>", "</b>"]


# ---------------------------------------------------------------------------
# Unicode (CJK) content is unaffected by the masking pass
# ---------------------------------------------------------------------------

def test_extract_links_handles_full_width_prose_around_real_links() -> None:
    content = "日本語の本文です。詳細は[リンク](https://example.test/ja)を参照。"
    links = md.extract_links(content)
    assert len(links) == 1
    assert links[0]["url"] == "https://example.test/ja"
    assert links[0]["text"] == "リンク"


# ---------------------------------------------------------------------------
# inventory() no longer relies on the fragile whole-content string replace
# ---------------------------------------------------------------------------

def test_inventory_raw_html_survives_duplicate_text_outside_the_fence() -> None:
    # Regression guard: the old heuristic did
    # `content.replace(block["code"], "")`, which stripped *every*
    # occurrence of a fenced block's text, including identical HTML that
    # appears for real outside the fence.
    content = "<b>bold</b>\n\n```\n<b>bold</b>\n```\n\n<b>bold</b>\n"
    result = md.inventory(content)
    assert result["raw_html_count"] == 4  # two real <b>bold</b>, open+close each
    assert result["code_block_count"] == 1


# ---------------------------------------------------------------------------
# data: URI classification (extraction only, never decode/execute/fetch)
# ---------------------------------------------------------------------------

def test_classify_data_uri_returns_none_for_non_data_values() -> None:
    assert md.classify_data_uri("https://example.test/a") is None
    assert md.classify_data_uri("") is None


def test_classify_data_uri_parses_base64_image() -> None:
    result = md.classify_data_uri("data:image/png;base64,iVBORw0KGgo=")
    assert result == {
        "mime_type": "image/png",
        "is_base64": True,
        "encoded_size": len("iVBORw0KGgo="),
    }


def test_classify_data_uri_defaults_mime_type_when_omitted() -> None:
    result = md.classify_data_uri("data:,A%20brief%20note")
    assert result == {
        "mime_type": "text/plain",
        "is_base64": False,
        "encoded_size": len("A%20brief%20note"),
    }


def test_classify_data_uri_keeps_charset_param_without_treating_it_as_base64() -> None:
    result = md.classify_data_uri("data:text/plain;charset=utf-8,hello")
    assert result == {
        "mime_type": "text/plain",
        "is_base64": False,
        "encoded_size": len("hello"),
    }


def test_extract_images_classifies_data_uri_without_decoding() -> None:
    content = "![alt](data:image/png;base64,iVBORw0KGgo=)"
    images = md.extract_images(content)
    assert len(images) == 1
    assert images[0]["url"] == "data:image/png;base64,iVBORw0KGgo="
    assert images[0]["data_uri"] == {
        "mime_type": "image/png",
        "is_base64": True,
        "encoded_size": len("iVBORw0KGgo="),
    }


def test_extract_links_data_uri_field_is_none_for_ordinary_links() -> None:
    links = md.extract_links("[a](https://example.test/a)")
    assert links[0]["data_uri"] is None


def test_extract_urls_still_collects_data_uris_verbatim() -> None:
    content = "![alt](data:image/png;base64,iVBORw0KGgo=)"
    assert md.extract_urls(content) == ["data:image/png;base64,iVBORw0KGgo="]
