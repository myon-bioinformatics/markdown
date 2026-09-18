from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("gradio")
pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import gradio_app  # noqa: E402


@pytest.fixture()
def gradio_url(free_port):
    port = free_port
    demo = gradio_app.build_app()
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        prevent_thread_lock=True,
        show_error=True,
        quiet=True,
        inbrowser=False,
    )
    try:
        time.sleep(1)  # give the server a moment before the first request
        yield f"http://127.0.0.1:{port}"
    finally:
        demo.close()


def test_gradio_analyze_populates_outputs(gradio_url, browser) -> None:
    """Fill the Markdown textbox, click Analyze, and check every output panel."""
    page = browser.new_page()
    try:
        page.goto(gradio_url, wait_until="networkidle")

        page.get_by_label("Markdown", exact=True).fill(
            "# Title\n\n[docs](https://example.com)\n\n![alt text](img.png)\n"
        )
        page.get_by_role("button", name="Analyze").click()
        page.wait_for_function(
            "document.querySelector('.cm-content')?.textContent.includes('heading_count')"
        )

        assert page.get_by_label("Headings").input_value() == "# Title"
        assert page.get_by_label("Links").input_value() == "- docs: https://example.com"
        assert page.get_by_label("Images").input_value() == "- alt text: img.png"

        summary_text = page.locator(".cm-content").first.inner_text()
        assert '"heading_count": 1' in summary_text
        assert '"link_count": 1' in summary_text
        assert '"image_count": 1' in summary_text
        assert "https://example.com" in summary_text
    finally:
        page.close()


def test_gradio_analyze_empty_input_shows_placeholders(gradio_url, browser) -> None:
    page = browser.new_page()
    try:
        page.goto(gradio_url, wait_until="networkidle")
        page.get_by_label("Markdown", exact=True).fill("")
        page.get_by_role("button", name="Analyze").click()
        page.wait_for_function(
            "document.querySelector('.cm-content')?.textContent.includes('heading_count')"
        )
        assert page.get_by_label("Headings").input_value() == "(none)"
        assert page.get_by_label("Links").input_value() == "(none)"
        assert page.get_by_label("Images").input_value() == "(none)"
    finally:
        page.close()
