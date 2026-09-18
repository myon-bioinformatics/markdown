"""A minimal OpenAI-compatible chat completions server, stdlib only.

Real chat UIs (Open WebUI, LibreChat, ...) talk to a "model" over the
OpenAI API shape: ``GET /v1/models`` to discover what's available, then
``POST /v1/chat/completions`` to get a reply. This mocks exactly that
shape — no LLM, no network call out — so a real product's own UI can be
pointed at it and its *rendering* of an assistant reply can be verified
against this repo's own ``markdown.py``-generated Markdown, the same
``render_assistant_turn()`` keyword logic ``chat_ui_demo.py`` already
uses for its own (generic, no-product) chat mock.

Supports both streaming (SSE, ``"stream": true``, what real chat UIs
normally request) and non-streaming (plain JSON) completions.

Run with: ``python demos/openai_compat_mock.py`` (default port 8090, override
with ``PORT``). No dependencies beyond the stdlib.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

from chat_ui_demo import render_assistant_turn  # noqa: E402

MODEL_ID = "markdown-demo-model"


def _models_payload() -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": 0,
                "owned_by": "markdown-demo",
            }
        ],
    }


def _last_user_message(body: dict) -> str:
    messages = body.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            # Some clients send content as a list of {"type": "text", "text": ...} parts.
            if isinstance(content, list):
                return "".join(part.get("text", "") for part in content if isinstance(part, dict))
            return str(content)
    return ""


def _completion_payload(reply_text: str) -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _stream_chunks(reply_text: str):
    chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    def _chunk(delta: dict, finish_reason: str | None) -> str:
        payload = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": MODEL_ID,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(payload)}\n\n"

    yield _chunk({"role": "assistant"}, None)
    yield _chunk({"content": reply_text}, None)
    yield _chunk({}, "stop")
    yield "data: [DONE]\n\n"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
        if self.path.rstrip("/").endswith("/models"):
            self._send_json(_models_payload())
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._send_json({"error": "not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON body"}, status=400)
            return

        reply_text = render_assistant_turn(_last_user_message(body))

        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            for chunk in _stream_chunks(reply_text):
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
            return

        self._send_json(_completion_payload(reply_text))

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (stdlib signature)
        sys.stderr.write("openai_compat_mock: " + (format % args) + "\n")


def serve(host: str = "127.0.0.1", port: int = 8090) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"openai_compat_mock listening on http://{host}:{port}/v1", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    serve(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8090")),
    )
