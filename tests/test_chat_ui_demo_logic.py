"""No-browser coverage for chat_ui_demo's rendering logic.

``render_assistant_turn`` / ``respond`` import neither gradio nor any chat
framework at module scope — plain Python, testable as a one-liner, matching
``demos/gradio_app.py``'s ``analyze()``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import chat_ui_demo as chat_ui  # noqa: E402
import markdown as md  # noqa: E402


def test_table_reply_renders_a_real_markdown_table() -> None:
    reply = chat_ui.render_assistant_turn("Show me a results table")
    assert "| metric | value |" in reply
    assert "| loss | 0.041 |" in reply
    html = md.markdown_to_html(reply)
    assert "<table>" in html
    assert "<th>metric</th>" in html
    assert "<td>loss</td>" in html


def test_code_reply_renders_a_fenced_block() -> None:
    reply = chat_ui.render_assistant_turn("show me some code")
    assert "```python" in reply
    assert "md.bold" in reply


def test_list_reply_renders_bullets() -> None:
    reply = chat_ui.render_assistant_turn("give me a todo list")
    assert "- review the PR" in reply
    assert "- ship it" in reply


def test_default_reply_uses_bold_and_italic() -> None:
    reply = chat_ui.render_assistant_turn("hello there")
    assert "**Got it.**" in reply
    assert "*Ask for a table, code, or list to see more.*" in reply


def test_respond_appends_user_then_assistant_turn() -> None:
    cleared, history = chat_ui.respond("table please", [])
    assert cleared == ""
    assert history[0] == {"role": "user", "content": "table please"}
    assert history[1]["role"] == "assistant"
    assert "| metric | value |" in history[1]["content"]


def test_respond_preserves_prior_history() -> None:
    _, first = chat_ui.respond("hello", [])
    _, second = chat_ui.respond("now a list please", first)
    assert len(second) == 4
    assert second[:2] == first


def test_sample_conversation_is_well_formed() -> None:
    assert chat_ui.SAMPLE_CONVERSATION[0]["role"] == "user"
    assert chat_ui.SAMPLE_CONVERSATION[1]["role"] == "assistant"
    assert "| metric | value |" in chat_ui.SAMPLE_CONVERSATION[1]["content"]
