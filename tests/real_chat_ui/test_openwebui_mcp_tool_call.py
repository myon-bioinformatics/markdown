"""Real Open WebUI, driven through its actual native MCP tool-call round trip.

test_openwebui_docker.py proves a real product renders markdown.py output
for a plain assistant reply. This goes one step further: register a real
MCP tool server (mcp-toolcall-lab's openwebui_mcp_mock.py, Streamable HTTP --
the same transport Open WebUI's own MCP client speaks natively, confirmed
from its source at backend/open_webui/utils/mcp/client.py) as a
TOOL_SERVER_CONNECTIONS entry, select it through the real per-chat "Tools"
picker in the message input (the same click path a real user takes -- not a
backend shortcut), send a message that should trigger a tool call, and
verify the tool's *actual* result round-trips back and renders as Markdown.

This is exactly the round trip docs/antipatterns.md exists for: when it
doesn't come back correctly (wrong selector, an unexpected MCP content
shape, a UI flow that changed), the failure here is real product behavior,
not a guess -- add what's learned as a new entry there.

Only runs with OPEN_WEBUI_BASE_URL and MOCK_MCP_SERVER_NAME set, which only
the real-chat-ui-smoke workflow sets (it also starts
demos/openai_compat_mock.py, configured to answer a triggering message with
a real OpenAI-style tool call, and mcp-toolcall-lab's openwebui_mcp_mock.py
as the MCP tool server Open WebUI actually calls).
"""

from __future__ import annotations

import os
import re

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

OPEN_WEBUI_BASE_URL = os.environ.get("OPEN_WEBUI_BASE_URL")
MOCK_MCP_SERVER_NAME = os.environ.get("MOCK_MCP_SERVER_NAME")

pytestmark = pytest.mark.skipif(
    not (OPEN_WEBUI_BASE_URL and MOCK_MCP_SERVER_NAME),
    reason="OPEN_WEBUI_BASE_URL / MOCK_MCP_SERVER_NAME not set -- only the "
    "real-chat-ui-smoke workflow (workflow_dispatch) sets these, since this "
    "test needs a real Open WebUI container with a real MCP tool server "
    "registered behind it",
)


@pytest.fixture(scope="module")
def browser():
    executable_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None
    with sync_playwright() as p:
        launched = p.chromium.launch(executable_path=executable_path)
        yield launched
        launched.close()


@pytest.fixture()
def page(browser):
    pg = browser.new_page()
    try:
        yield pg
    finally:
        pg.close()


def _dismiss_blocking_dialog(page) -> None:
    """See test_openwebui_docker.py's own copy for why -- the changelog
    modal fires on every run against this fresh auto-provisioned admin."""
    dialog = page.locator('div[role="dialog"][aria-modal="true"]')
    if dialog.count():
        page.keyboard.press("Escape")
        dialog.last.wait_for(state="hidden", timeout=5_000)


def _enable_mcp_tool_server(page) -> None:
    """Click through the real per-chat "Tools" picker (Wrench icon in the
    message input's Integrations menu) to turn on the registered MCP tool
    server for this chat -- the same click path a real user takes, not a
    backend/API shortcut, since the point of this test is to prove the real
    UI flow round-trips correctly."""
    page.locator("#integration-menu-button").click()
    page.get_by_role("button", name=re.compile(r"^Tools\b")).click()
    page.get_by_role("button", name=re.compile(re.escape(MOCK_MCP_SERVER_NAME))).click()
    # Close the menu the same way a user would (click elsewhere) rather than
    # Escape, which closes Modal.svelte-style dialogs, not this dropdown.
    page.locator("#chat-input").click()


def _send_message(page, text: str) -> None:
    _dismiss_blocking_dialog(page)
    chat_input = page.locator("#chat-input")
    chat_input.click()
    page.keyboard.type(text)
    page.keyboard.press("Enter")


def test_openwebui_mcp_tool_call_result_renders_in_the_real_ui(page) -> None:
    page.goto(OPEN_WEBUI_BASE_URL, wait_until="networkidle")
    page.wait_for_selector("#chat-input", timeout=30_000)
    _dismiss_blocking_dialog(page)

    _enable_mcp_tool_server(page)
    _send_message(page, "please find municipalities near Yokohama")

    container = page.locator("#response-content-container").last
    # A full round trip (tool call -> Open WebUI dispatches to the real MCP
    # server -> result -> second model call -> render) is slower than a
    # single-turn reply, hence the longer timeout than test_openwebui_docker.py.
    container.locator("table").wait_for(timeout=60_000)

    table = container.locator("table")
    assert table.locator("td", has_text="14109").count() >= 1
    assert table.locator("td", has_text=re.compile("yokohama", re.I)).count() >= 1
    assert table.locator("td", has_text=re.compile("kanagawa", re.I)).count() >= 1
