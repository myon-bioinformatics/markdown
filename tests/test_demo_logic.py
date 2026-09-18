"""No-browser, no-click coverage for the demo apps' actual logic.

``demos/gradio_app.py`` and ``demos/streamlit_app.py`` each keep their real
work in a plain function (``analyze`` / ``build_view``) that imports neither
``gradio`` nor ``streamlit`` at module scope. That means the behavior behind
each UI is a normal Python library call — testable (and runnable as a
one-liner) without installing a frontend framework, launching a server, or
driving a browser.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import gradio_app  # noqa: E402
import streamlit_app  # noqa: E402


def test_gradio_analyze_is_a_plain_function_call() -> None:
    headings, links, images, summary = gradio_app.analyze(
        "# Title\n\n[docs](https://example.com)\n\n![alt text](img.png)\n"
    )
    assert headings == "# Title"
    assert links == "- docs: https://example.com"
    assert images == "- alt text: img.png"
    payload = json.loads(summary)
    assert payload["heading_count"] == 1
    assert payload["link_count"] == 1
    assert payload["image_count"] == 1
    assert payload["urls"] == ["https://example.com", "img.png"]


def test_gradio_analyze_empty_input_shows_placeholders() -> None:
    headings, links, images, summary = gradio_app.analyze("")
    assert headings == "(none)"
    assert links == "(none)"
    assert images == "(none)"
    assert json.loads(summary)["heading_count"] == 0


def test_gradio_analyze_reads_uploaded_file(tmp_path: Path) -> None:
    md_file = tmp_path / "note.md"
    md_file.write_text("# From file\n", encoding="utf-8")
    headings, _, _, _ = gradio_app.analyze("ignored when a file is uploaded", str(md_file))
    assert headings == "# From file"


def test_streamlit_build_view_has_no_streamlit_import() -> None:
    # Checking sys.modules would be order-dependent in a full pytest run (other
    # test files legitimately import the real streamlit); what actually matters
    # is that streamlit_app's own module namespace never binds it, since
    # `import streamlit as st` in build_view()'s caller (main()) is local to
    # that function, not module scope.
    assert "streamlit" not in vars(streamlit_app)


def test_streamlit_build_view_counts_and_preview() -> None:
    view = streamlit_app.build_view("# Only Heading\n\nplain text, no links or images.\n")
    assert view["heading_count"] == 1
    assert view["link_count"] == 0
    assert view["image_count"] == 0
    assert "<h1>Only Heading</h1>" in view["html_preview"]


def test_streamlit_build_view_matches_default_fixture() -> None:
    content = streamlit_app.DEFAULT_FIXTURE.read_text(encoding="utf-8")
    view = streamlit_app.build_view(content)
    assert view["heading_count"] > 0
    assert view["link_count"] > 0
