"""No-server coverage for demos/openai_compat_mock.py's tool-call round trip.

The HTTP server itself is only exercised for real by
tests/real_chat_ui/test_openwebui_docker.py (which needs a live container),
but the logic that decides whether to issue a tool call and how to render a
tool's result back into Markdown is plain functions -- testable directly,
the same pattern tests/test_demo_logic.py already uses for the other demos.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import openai_compat_mock as mock  # noqa: E402


def test_offered_tool_call_function_name_matches_by_suffix() -> None:
    tools = [{"type": "function", "function": {"name": "mock-mcp_find_municipalities"}}]
    assert mock._offered_tool_call_function_name(tools) == "mock-mcp_find_municipalities"


def test_offered_tool_call_function_name_matches_bare_name() -> None:
    tools = [{"type": "function", "function": {"name": "find_municipalities"}}]
    assert mock._offered_tool_call_function_name(tools) == "find_municipalities"


def test_offered_tool_call_function_name_none_when_not_offered() -> None:
    tools = [{"type": "function", "function": {"name": "some_other_tool"}}]
    assert mock._offered_tool_call_function_name(tools) is None
    assert mock._offered_tool_call_function_name([]) is None


def test_tool_result_records_parses_flat_json_string_content() -> None:
    message = {"role": "tool", "content": '[{"code": "14109", "name": "Yokohama"}]'}
    assert mock._tool_result_records(message) == [{"code": "14109", "name": "Yokohama"}]


def test_tool_result_records_unwraps_mcp_content_block_layer() -> None:
    # The realistic shape: content is a JSON string of MCP content blocks,
    # and the block's own "text" field holds a second layer of JSON --
    # the actual tool result.
    message = {
        "role": "tool",
        "content": '[{"type": "text", "text": "[{\\"code\\": \\"14109\\", \\"name\\": \\"Yokohama\\"}]"}]',
    }
    assert mock._tool_result_records(message) == [{"code": "14109", "name": "Yokohama"}]


def test_tool_result_records_unwraps_open_webui_results_envelope() -> None:
    # Confirmed live (real-chat-ui-smoke run 35412247498): Open WebUI's own
    # middleware wraps the tool's return value in {"results": [...]} before
    # handing it to the model as the tool message's content -- one level up
    # from (and present even without) the MCP content-block layer above.
    message = {"role": "tool", "content": '{"results": [{"code": "14109", "name": "Yokohama"}]}'}
    assert mock._tool_result_records(message) == [{"code": "14109", "name": "Yokohama"}]


def test_tool_result_records_unwraps_results_envelope_inside_content_block() -> None:
    message = {
        "role": "tool",
        "content": '[{"type": "text", "text": "{\\"results\\": [{\\"code\\": \\"14109\\"}]}"}]',
    }
    assert mock._tool_result_records(message) == [{"code": "14109"}]


def test_tool_result_records_none_on_unparseable_content() -> None:
    assert mock._tool_result_records({"role": "tool", "content": "not json"}) is None


def test_render_tool_result_reply_builds_a_table_from_records() -> None:
    records = [{"code": "14109", "name": "Yokohama", "prefecture": "Kanagawa"}]
    reply = mock._render_tool_result_reply(records)
    assert "Municipalities" in reply
    assert "| code | name | prefecture |" in reply
    assert "| 14109 | Yokohama | Kanagawa |" in reply


def test_render_tool_result_reply_handles_empty_results() -> None:
    assert "No matches" in mock._render_tool_result_reply([])
    assert "No matches" in mock._render_tool_result_reply(None)


def test_tool_call_payload_shape() -> None:
    tool_call = mock._tool_call_payload("mock-mcp_find_municipalities", {"query": "Yokohama"})
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "mock-mcp_find_municipalities"
    assert tool_call["id"].startswith("call_")
    import json

    assert json.loads(tool_call["function"]["arguments"]) == {"query": "Yokohama"}
