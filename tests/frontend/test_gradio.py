"""Verify the real Gradio app's wiring (Blocks -> event handler -> outputs) over HTTP.

No browser, no clicking. Two clients talk to the launched ``demos/gradio_app.py``
and must agree with a plain ``analyze()`` call (whose own coverage is the demo
logic section of ``tests/test_tooling.py``):

- plain ``curl``: Gradio's backend is a FastAPI app, so calling a component's
  wired function is a plain HTTP job-submission protocol (POST to start, GET an
  SSE stream for the result). This proves the app is genuinely loosely coupled
  over HTTP, not just callable through gradio_client.
- ``gradio_client``: the app's own HTTP/websocket API, the same interface a real
  browser session would use, so this exercises the actual ``btn.click(...)`` wiring.
"""

from __future__ import annotations

import json, shutil, subprocess

import pytest

pytest.importorskip("gradio")
gradio_client = pytest.importorskip("gradio_client")

import gradio_app  # noqa: E402

CURL = shutil.which("curl")


@pytest.fixture()
def gradio_base_url(free_port, wait_until_up):
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
    base_url = f"http://127.0.0.1:{free_port}"
    try:
        wait_until_up(base_url, "gradio")
        yield base_url
    finally:
        demo.close()


@pytest.fixture()
def gradio_client_(gradio_base_url):
    return gradio_client.Client(gradio_base_url + "/")


def _curl_call(base_url: str, text: str, timeout: float = 15.0) -> tuple:
    """POST to start the job, then GET the SSE stream for its result — both via curl."""
    post = subprocess.run(
        [
            CURL, "-s", "-X", "POST", f"{base_url}/gradio_api/call/analyze",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"data": [text, None]}),
        ],
        capture_output=True, text=True, timeout=timeout, check=True,
    )
    event_id = json.loads(post.stdout)["event_id"]

    stream = subprocess.run(
        [CURL, "-s", "-N", "--max-time", str(timeout), f"{base_url}/gradio_api/call/analyze/{event_id}"],
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


def test_gradio_api_matches_direct_call(gradio_client_) -> None:
    text = "# Title\n\n[docs](https://example.com)\n\n![alt text](img.png)\n"
    api_result = gradio_client_.predict(text, None, api_name="/analyze")
    assert tuple(api_result) == gradio_app.analyze(text)


def test_gradio_api_empty_input_matches_direct_call(gradio_client_) -> None:
    api_result = gradio_client_.predict("", None, api_name="/analyze")
    assert tuple(api_result) == gradio_app.analyze("")
