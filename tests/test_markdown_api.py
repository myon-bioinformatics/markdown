from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

FIXTURES = ROOT / "fixtures"


def test_save_and_read_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    message = md.save_markdown("# Hi\n\nbody\n", str(path))
    assert message.startswith("Saved successfully:")
    result = md.read_markdown(str(path), count_hashtags=True)
    assert result["success"] is True
    assert result["content"].startswith("# Hi")
    assert result["hashtag_count"] == 1


def test_read_missing_file(tmp_path: Path) -> None:
    result = md.read_markdown(str(tmp_path / "missing.md"))
    assert result["success"] is False
    assert "Error reading file" in result["content"]


def test_extract_and_split_sections() -> None:
    content = "# A\n\npara\n\n## B\n\nmore\n"
    sections = md.extract_sections(content)
    assert sections == [
        {"level": 1, "title": "A"},
        {"level": 2, "title": "B"},
    ]
    parts = md.split_sections(content)
    assert parts[0]["level"] == 1
    assert "para" in parts[0]["content"]
    assert parts[1]["title"] == "B"


def test_builders_and_focused_html_markdown() -> None:
    assert md.make_link("Docs", "https://example.com") == "[Docs](https://example.com)"
    assert md.make_image("Alt", "a.png", "t") == '![Alt](a.png "t")'

    html_img = '<img src="a.png" alt="Alt" title="t" />'
    assert md.html_image_to_markdown(html_img) == '![Alt](a.png "t")'
    assert 'src="a.png"' in md.markdown_image_to_html('![Alt](a.png "t")')

    html_a = '<a href="https://example.com" title="Ex">Docs</a>'
    assert md.html_link_to_markdown(html_a) == '[Docs](https://example.com "Ex")'
    assert 'href="https://example.com"' in md.markdown_link_to_html(
        '[Docs](https://example.com "Ex")'
    )


def test_html_markdown_subset_roundtrip_ish() -> None:
    html = "<h1>Title</h1><p>Hello <strong>world</strong> and <a href=\"u\">link</a>.</p>"
    converted = md.html_to_markdown(html)
    assert converted.startswith("# Title")
    assert "**world**" in converted
    assert "[link](u)" in converted

    markdown = "# Title\n\nHello **world** and [link](https://ex.com).\n\n```py\nprint(1)\n```\n"
    html_out = md.markdown_to_html(markdown)
    assert "<h1>Title</h1>" in html_out
    assert "<strong>world</strong>" in html_out
    assert "<pre><code" in html_out


def test_is_probably_url() -> None:
    assert md.is_probably_url("https://example.com/a")
    assert not md.is_probably_url("logo.png")


def test_inventory_basic() -> None:
    content = (FIXTURES / "vscode_readme_snippet.md").read_text(encoding="utf-8")
    inv = md.inventory(content)
    assert inv["heading_count"] >= 3
    assert inv["image_count"] >= 1
    assert inv["link_count"] >= 2
    assert inv["code_block_count"] >= 1
    assert inv["horizontal_rule_count"] >= 1
    assert "supported" in inv and "unsupported" in inv
