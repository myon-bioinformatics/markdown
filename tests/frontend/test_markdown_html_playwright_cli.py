"""Verify markdown.py's own HTML output is real, renderable HTML — no chat UI needed.

The chat UI demo (``test_chat_ui_screen.py``) proves the generation helpers
render correctly *inside a chat screen*, but that screen is incidental — the
thing actually worth checking is ``markdown_to_html()``'s output, and that
doesn't require any app, server, or UI to view: it's just an HTML file, and
Playwright ships a CLI for exactly this (``python -m playwright screenshot``),
the same "reach for the tool's own CLI" approach this repo already uses with
curl for HTTP APIs. No ``sync_playwright()`` script, no server, no browser
fixture — one subprocess call against a ``file://`` path.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

pytest.importorskip("playwright")

import markdown as md  # noqa: E402

CONTENT = md.section(
    "Results",
    [
        md.table(["metric", "value"], [["loss", "0.041"], ["iou", "0.87"]]),
        md.bullet_list(["review the PR", "ship it"]),
        f"{md.bold('Done.')} {md.italic('See the table above.')}\n",
    ],
)


def _run_playwright_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "playwright", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _skip_if_browser_missing(result: subprocess.CompletedProcess) -> None:
    if result.returncode != 0 and "playwright install" in result.stderr:
        pytest.skip(
            "chromium not installed for this Playwright version here — "
            "run `playwright install chromium` (CI does this automatically)"
        )
    assert result.returncode == 0, result.stderr


def _html_document(body: str) -> str:
    return (
        "<html><head><style>"
        + md.default_stylesheet()
        + "</style></head><body>"
        + body
        + "</body></html>"
    )


def test_cli_screenshot_renders_generated_html(tmp_path) -> None:
    html_file = tmp_path / "reply.html"
    html_file.write_text(_html_document(md.markdown_to_html(CONTENT)), encoding="utf-8")
    png_file = tmp_path / "reply.png"

    result = _run_playwright_cli(
        "screenshot", "--full-page", html_file.as_uri(), str(png_file)
    )
    _skip_if_browser_missing(result)

    assert png_file.exists()
    assert png_file.stat().st_size > 1000  # a blank/failed render is a tiny file


def test_cli_pdf_renders_generated_html(tmp_path) -> None:
    html_file = tmp_path / "reply.html"
    html_file.write_text(_html_document(md.markdown_to_html(CONTENT)), encoding="utf-8")
    pdf_file = tmp_path / "reply.pdf"

    result = _run_playwright_cli("pdf", html_file.as_uri(), str(pdf_file))
    _skip_if_browser_missing(result)

    assert pdf_file.exists()
    assert pdf_file.read_bytes().startswith(b"%PDF")
