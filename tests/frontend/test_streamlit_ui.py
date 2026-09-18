from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "demos" / "streamlit_app.py"


def _wait_until_up(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"streamlit app did not start in time: {last_error}")


@pytest.fixture()
def streamlit_url(free_port):
    port = free_port
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_PATH),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.address",
            "127.0.0.1",
            "--browser.gatherUsageStats",
            "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_up(url)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_streamlit_default_fixture_metrics(streamlit_url, browser) -> None:
    """The app loads with the default vscode README fixture and shows its inventory."""
    page = browser.new_page()
    try:
        page.goto(streamlit_url, wait_until="networkidle")
        page.wait_for_selector("[data-testid='stMetricValue']")
        metrics = page.locator("[data-testid='stMetricValue']").all_inner_texts()
        assert len(metrics) == 5
        heading_count, link_count, image_count, code_count, html_count = (
            int(v) for v in metrics
        )
        assert heading_count > 0
        assert link_count > 0

        tabs = page.get_by_role("tab").all_inner_texts()
        assert tabs == ["Headings", "Links", "Images", "Code blocks", "HTML"]
    finally:
        page.close()


def test_streamlit_editing_source_updates_metrics(streamlit_url, browser) -> None:
    page = browser.new_page()
    try:
        page.goto(streamlit_url, wait_until="networkidle")
        page.wait_for_selector("[data-testid='stMetricValue']")

        textarea = page.locator("textarea").first
        textarea.click()
        textarea.fill("# Only Heading\n\nplain text, no links or images.\n")
        textarea.blur()

        page.wait_for_function(
            "document.querySelectorAll(\"[data-testid='stMetricValue']\")[0]?.textContent === '1'"
        )
        metrics = page.locator("[data-testid='stMetricValue']").all_inner_texts()
        assert metrics == ["1", "0", "0", "0", "0"]
    finally:
        page.close()
