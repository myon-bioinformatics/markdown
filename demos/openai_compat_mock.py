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

Also supports one deterministic OpenAI-style *tool call* round trip (see
``TOOL_CALL_TRIGGER`` below), so a real product's own native function-calling
UI (tool selection, the "running tool..." indicator, rendering the model's
follow-up reply) can be exercised end to end against a real MCP tool server
(e.g. mcp-toolcall-lab's ``openwebui_mcp_mock.py``) instead of only the
plain-text reply path above.

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

import markdown as md  # noqa: E402
from chat_ui_demo import render_assistant_turn  # noqa: E402

MODEL_ID = "markdown-demo-model"

# A tool call fires when the user's message contains this phrase *and* the
# request offers at least one tool whose function name ends with
# TOOL_CALL_FUNCTION_SUFFIX (real tool-server-backed function names are
# prefixed by the caller, e.g. "mock-mcp_find_municipalities" -- matching by
# suffix rather than hardcoding the prefix keeps this independent of whatever
# server id the tool server connection was registered under).
TOOL_CALL_TRIGGER = "find municipalities"
TOOL_CALL_FUNCTION_SUFFIX = "find_municipalities"
TOOL_CALL_ARGUMENTS = {"query": "Yokohama"}


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


def _offered_tool_call_function_name(tools_offered: list) -> str | None:
    """Return the exact function name to call, taken from the caller's own
    ``tools`` list rather than hardcoded, since a tool-server-backed function
    name is prefixed by the caller (e.g. with its server id) before it
    reaches the model."""
    for tool in tools_offered or []:
        name = (tool.get("function") or {}).get("name", "")
        if name == TOOL_CALL_FUNCTION_SUFFIX or name.endswith("_" + TOOL_CALL_FUNCTION_SUFFIX):
            return name
    return None


def _tool_call_payload(function_name: str, arguments: dict) -> dict:
    return {
        "id": f"call_{uuid.uuid4().hex}",
        "type": "function",
        "function": {"name": function_name, "arguments": json.dumps(arguments)},
    }


def _tool_call_completion_payload(tool_call: dict) -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _stream_tool_call_chunks(tool_call: dict):
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

    yield _chunk({"role": "assistant", "tool_calls": [{**tool_call, "index": 0}]}, None)
    yield _chunk({}, "tool_calls")
    yield "data: [DONE]\n\n"


def _tool_result_records(tool_message: dict):
    """Parse a tool-result message's ``content`` into Python data.

    OpenAI's own wire format always makes ``content`` a plain string, but an
    MCP round trip commonly nests a *second* layer of JSON inside it: the
    string decodes to a list of MCP content blocks
    (``[{"type": "text", "text": "<json>"}]``), and it's that block's own
    ``text`` field that holds the actual tool result as JSON. Unwrap both
    layers; return None (never guess) if either fails to parse."""
    content = tool_message.get("content", "")
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", "replace")
    if isinstance(content, list):
        # Content blocks given directly rather than as a JSON string.
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None

    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and {"type", "text"} <= set(parsed[0]):
        try:
            parsed = json.loads("".join(block.get("text", "") for block in parsed))
        except (json.JSONDecodeError, TypeError):
            return None

    # Open WebUI's own middleware wraps a tool's return value in a small
    # envelope dict (confirmed live: {"results": [...]}) before handing it
    # to the model as the tool message's content -- one level up from the
    # MCP content-block layer just unwrapped above, and present even when
    # content was a flat JSON string with no content-block layer at all.
    if isinstance(parsed, dict):
        for key in ("results", "result"):
            if isinstance(parsed.get(key), list):
                return parsed[key]

    return parsed


def _render_tool_result_reply(records) -> str:
    """Render a tool call's result as Markdown, the same way render_assistant_turn()
    renders a canned reply -- so the real product's own Markdown renderer is
    exercised on the *actual* MCP round trip, not a hardcoded string."""
    if isinstance(records, dict):
        records = [records]
    if not records or not isinstance(records, list) or not isinstance(records[0], dict):
        return md.section("Municipalities", ["No matches."])

    columns = list(records[0].keys())
    rows = [[str(row.get(col, "")) for col in columns] for row in records]
    return md.section("Municipalities", [md.table(columns, rows)])


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, chunks) -> None:
        """Send an SSE stream, then force the connection closed.

        An SSE body has neither Content-Length nor chunked Transfer-Encoding,
        so under HTTP/1.1 keep-alive (this handler's default) the client has
        no framing signal for where the body ends -- only a connection close
        tells it. Claiming "Connection: keep-alive" anyway (the previous
        behavior) worked for exactly one request per connection: the first
        request on a fresh connection has nothing to get confused about, but
        the *second* request the client tries to send on what it thinks is
        the same still-open, still-idle connection lands on a socket whose
        response the server never actually terminated -- confirmed live: two
        CI runs in a row had every real-chat-ui-smoke test after the first
        one time out waiting for content that was never going to arrive. See
        docs/antipatterns.md.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.flush()
        self.close_connection = True

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

        messages = body.get("messages", [])
        last_message = messages[-1] if messages else {}
        tools_offered = body.get("tools") or []

        # Always-on, one-line-per-request summary: cheap, and the fastest way
        # to tell "the tool-selection UI didn't actually enable the tool" (no
        # tool names here) apart from "it did, but this mock's own trigger
        # logic didn't match" (names present, no tool_calls issued) -- from
        # this log alone, without needing a screenshot artifact.
        tool_names = [(t.get("function") or {}).get("name", "") for t in tools_offered]
        sys.stderr.write(
            f"openai_compat_mock: chat.completions last_role={last_message.get('role')!r} "
            f"tools_offered={tool_names!r} last_user_message={_last_user_message(body)!r}\n"
        )

        if last_message.get("role") == "tool":
            # The caller already executed the tool call we issued below and
            # is now handing back its result -- render the final answer from
            # that *real* result, not a canned string.
            reply_text = _render_tool_result_reply(_tool_result_records(last_message))
        else:
            function_name = _offered_tool_call_function_name(tools_offered)
            if function_name and TOOL_CALL_TRIGGER in _last_user_message(body).lower():
                tool_call = _tool_call_payload(function_name, TOOL_CALL_ARGUMENTS)
                if body.get("stream"):
                    self._send_sse(_stream_tool_call_chunks(tool_call))
                    return
                self._send_json(_tool_call_completion_payload(tool_call))
                return

            reply_text = render_assistant_turn(_last_user_message(body))

        if body.get("stream"):
            self._send_sse(_stream_chunks(reply_text))
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
