"""Mirror tests: markdown.py must agree with independent JS implementations.

markdown-it (CommonMark) and marked (GFM) render every Markdown file in this
repository, linkedom reads the HTML; string-width measures display widths. No
browser is involved. Neither side is the oracle: a disagreement is a lead.
Known dialect difference: marked autolinks bare URLs, markdown.py and CommonMark
do not, so links are compared with markdown-it only.

Needs ``npm ci --prefix tests/mirror`` (CI does this); skipped without it.
"""
from __future__ import annotations

import collections
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import markdown as md

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "tests" / "mirror"
pytestmark = pytest.mark.skipif(
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
    files = sorted(p for p in ROOT.rglob("*.md") if "node_modules" not in p.parts and ".git" not in p.parts)
    texts = [p.read_text(encoding="utf-8") for p in files]
    done = subprocess.run(["node", str(MIRROR / "facts.mjs")], input=json.dumps({"markdown": texts, "width": WIDTHS}),
                          capture_output=True, text=True, check=True, timeout=120)
    return files, texts, json.loads(done.stdout)


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


def test_display_width_agrees_with_string_width(readers):
    expected = readers[2]["string-width"]
    actual = [md._display_width(text) for text in WIDTHS]
    assert [(t, a, e) for t, a, e in zip(WIDTHS, actual, expected) if a != e] == []
