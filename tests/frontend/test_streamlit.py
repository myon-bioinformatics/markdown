"""Verify the real Streamlit script ``demos/streamlit_app.py``, with no browser at all.

- ``streamlit.testing.v1.AppTest`` runs the script exactly as ``streamlit run``
  would (same script, same session state), but in-process and headless —
  driving widgets and reading rendered output purely through its Python API.
  That exercises the actual ``st.metric``/``st.tabs`` wiring instead of only
  ``build_view()`` (whose own coverage is the demo logic section of
  ``tests/test_tooling.py``).
- plain ``curl``: Streamlit has no simple request/response HTTP API for widget
  interactions (reruns go over a stateful websocket, which is AppTest's job),
  but curl can verify that the real process launched by ``streamlit run`` comes
  up and serves HTTP: its health endpoint and the initial page shell.
"""

from __future__ import annotations

import shutil, subprocess, sys
from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "demos" / "streamlit_app.py"
CURL = shutil.which("curl")


def test_streamlit_default_fixture_metrics() -> None:
    at = AppTest.from_file(str(APP_PATH)).run(timeout=15)
    assert not at.exception

    metrics = [m.value for m in at.metric]
    assert len(metrics) == 5
    heading_count, link_count, *_ = (int(v) for v in metrics)
    assert heading_count > 0
    assert link_count > 0

    assert [t.label for t in at.tabs] == [
        "Headings",
        "Links",
        "Images",
        "Code blocks",
        "HTML",
    ]


def test_streamlit_editing_source_updates_metrics() -> None:
    at = AppTest.from_file(str(APP_PATH)).run(timeout=15)
    at.text_area[0].set_value("# Only Heading\n\nplain text, no links or images.\n")
    at.run(timeout=15)

    assert not at.exception
    assert [m.value for m in at.metric] == ["1", "0", "0", "0", "0"]


@pytest.fixture()
def streamlit_base_url(free_port, wait_until_up):
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(APP_PATH),
            "--server.port", str(free_port),
            "--server.headless", "true",
            "--server.address", "127.0.0.1",
            "--browser.gatherUsageStats", "false",
        ],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(ROOT),
    )
    url = f"http://127.0.0.1:{free_port}"
    try:
        wait_until_up(url, "streamlit")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.skipif(CURL is None, reason="curl is not available on this system")
def test_streamlit_curl_health_and_index(streamlit_base_url) -> None:
    health = subprocess.run(
        [CURL, "-s", f"{streamlit_base_url}/_stcore/health"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    assert health.stdout.strip() == "ok"

    index = subprocess.run(
        [CURL, "-s", streamlit_base_url],
        capture_output=True, text=True, timeout=10, check=True,
    )
    assert "<title>" in index.stdout
