"""Verify the real Gradio app's wiring (Blocks -> event handler -> outputs).

No browser, no clicking: ``gradio_client`` talks to the launched app's own
HTTP/websocket API, the same interface a real browser session would use,
so this exercises the actual ``btn.click(...)`` wiring in
``demos/gradio_app.py`` instead of only the ``analyze()`` function directly
(see ``tests/test_demo_logic.py`` for that plain-function-call coverage).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("gradio")
gradio_client = pytest.importorskip("gradio_client")

ROOT = Path(__file__).resolve().parents[2]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import gradio_app  # noqa: E402


@pytest.fixture()
def gradio_client_(free_port):
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
        yield gradio_client.Client(f"http://127.0.0.1:{free_port}/")
    finally:
        demo.close()


def test_gradio_api_matches_direct_call(gradio_client_) -> None:
    text = "# Title\n\n[docs](https://example.com)\n\n![alt text](img.png)\n"
    api_result = gradio_client_.predict(text, None, api_name="/_run")
    assert tuple(api_result) == gradio_app.analyze(text)


def test_gradio_api_empty_input_matches_direct_call(gradio_client_) -> None:
    api_result = gradio_client_.predict("", None, api_name="/_run")
    assert tuple(api_result) == gradio_app.analyze("")
