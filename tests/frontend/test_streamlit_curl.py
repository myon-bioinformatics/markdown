"""Reachability check for the real Streamlit server via plain ``curl``.

Unlike Gradio, Streamlit doesn't expose a simple request/response HTTP API
for widget interactions — reruns are driven over a stateful websocket
protocol, which ``AppTest`` (see ``test_streamlit_ui.py``) is the right tool
for. What curl *can* verify with no Python client at all is that the real
process launched by ``streamlit run`` comes up and serves HTTP: its health
endpoint and the initial page shell.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "demos" / "streamlit_app.py"
CURL = shutil.which("curl")


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
def streamlit_base_url(free_port):
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
        _wait_until_up(url)
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
