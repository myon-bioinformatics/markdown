from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def test_stylesheet_helpers_exported() -> None:
    assert "alert_stylesheet" in md.__all__
    assert "default_stylesheet" in md.__all__


def test_alert_stylesheet_is_nonempty_and_has_hooks() -> None:
    css = md.alert_stylesheet()
    assert css.strip()
    assert ".markdown-alert" in css
    assert ".markdown-alert-title" in css
    assert ".markdown-alert-note" in css
    assert 'data-alert-flavor="github"' in css
    assert "url(" not in css
    assert "http://" not in css
    assert "https://" not in css


def test_default_stylesheet_includes_alerts_and_common_blocks() -> None:
    alert = md.alert_stylesheet()
    css = md.default_stylesheet()
    assert css.strip()
    assert alert in css
    assert "table" in css
    assert "blockquote" in css
    assert "pre" in css
    assert "code" in css
    assert re.search(r"\bh1\b", css)
    assert "url(" not in css
    assert "http://" not in css
    assert "https://" not in css


def test_readme_embed_pattern_is_valid_html() -> None:
    src = md.section("Summary", [md.table(["a", "b"], [[1, 2]]), md.blockquote("quoted")])
    html = "<style>" + md.default_stylesheet() + "</style>\n" + md.markdown_to_html(src)
    assert html.startswith("<style>")
    assert "</style>" in html
    assert "<table>" in html
    assert "<blockquote>" in html
