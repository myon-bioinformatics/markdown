"""Hit the real Gradio HTTP API with plain ``curl`` — no Python client library.

Gradio's backend is a FastAPI app: calling a component's wired function is a
plain HTTP job-submission protocol (POST to start, GET an SSE stream for the
result). Driving it with ``curl`` (any Ubuntu box has it) proves the app is
genuinely loosely coupled over HTTP, not just callable through gradio_client.
See ``test_gradio_ui.py`` for the gradio_client-based equivalent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("gradio")

ROOT = Path(__file__).resolve().parents[2]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import gradio_app  # noqa: E402

CURL = shutil.which("curl")


@pytest.fixture()
def gradio_base_url(free_port):
    demo = gradio_app.build_app()
    demo.queue()
    demo.launch(
        server_name="127.0.0.1",
        server_port=free_port,
        prevent_thread_lock=True,
        show_error=True,
        quiet=True,
        inbrowser=False,
    )
    try:
        time.sleep(1)  # give the server a moment before the first request
        yield f"http://127.0.0.1:{free_port}"
    finally:
        demo.close()


def _curl_call(base_url: str, text: str, timeout: float = 15.0) -> tuple:
    """POST to start the job, then GET the SSE stream for its result — both via curl."""
    post = subprocess.run(
        [
            CURL, "-s", "-X", "POST", f"{base_url}/gradio_api/call/_run",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"data": [text, None]}),
        ],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    event_id = json.loads(post.stdout)["event_id"]

    stream = subprocess.run(
        [CURL, "-s", "-N", "--max-time", str(timeout), f"{base_url}/gradio_api/call/_run/{event_id}"],
        capture_output=True, text=True, timeout=timeout + 5, check=True,
    )
    data_line = next(
        line for line in stream.stdout.splitlines() if line.startswith("data:")
    )
    return tuple(json.loads(data_line[len("data:"):]))


@pytest.mark.skipif(CURL is None, reason="curl is not available on this system")
def test_gradio_curl_matches_direct_call(gradio_base_url) -> None:
    text = "# Title\n\n[docs](https://example.com)\n\n![alt text](img.png)\n"
    assert _curl_call(gradio_base_url, text) == gradio_app.analyze(text)


@pytest.mark.skipif(CURL is None, reason="curl is not available on this system")
def test_gradio_curl_empty_input_matches_direct_call(gradio_base_url) -> None:
    assert _curl_call(gradio_base_url, "") == gradio_app.analyze("")
