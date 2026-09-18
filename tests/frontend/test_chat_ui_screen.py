"""Verify the chat_ui_demo's actual rendered screen — this one has a chat screen.

Unlike the gradio_app.py / streamlit_app.py demos, ``chat_ui_demo.py`` *is* a
chat screen (a `gr.Chatbot` bubble history), so — unlike this repo's other
frontend tests, which avoid clicking because there's nothing to look at —
here we type into the message box, click Send, and check what actually
rendered. That's the point of this demo: proving markdown.py's generation
helpers (table/code_block/bullet_list/bold/italic) produce correctly
rendered HTML in a real chat UI, not just correct strings.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("gradio")
pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)

import chat_ui_demo  # noqa: E402


@pytest.fixture()
def chat_ui_url(free_port):
    demo = chat_ui_demo.build_app()
    demo.launch(
        server_name="127.0.0.1",
        server_port=free_port,
        prevent_thread_lock=True,
        show_error=True,
        quiet=True,
        inbrowser=False,
    )
    try:
        time.sleep(1)
        yield f"http://127.0.0.1:{free_port}"
    finally:
        demo.close()


def test_initial_conversation_renders_a_real_table(chat_ui_url, browser) -> None:
    page = browser.new_page()
    try:
        page.goto(chat_ui_url, wait_until="networkidle")
        assert page.get_by_text("Show me a results table").count() >= 1

        # Assert actual <table> DOM structure, not just visible text — this repo's own
        # markdown_to_html() does NOT emit <table> by design (see test_chat_ui_demo_logic.py),
        # so text-only assertions here would also pass for an unparsed plain-text fallback.
        table = page.locator("table").first
        assert table.locator("th").all_inner_texts() == ["metric", "value"]
        assert table.locator("tbody tr").count() == 3
        assert table.locator("tbody tr").first.locator("td").all_inner_texts() == ["loss", "0.041"]
    finally:
        page.close()


def test_sending_a_code_message_renders_a_syntax_highlighted_block(chat_ui_url, browser) -> None:
    page = browser.new_page()
    try:
        page.goto(chat_ui_url, wait_until="networkidle")
        page.get_by_test_id("textbox").fill("show me some code")
        page.get_by_role("button", name="Send").click()
        page.wait_for_selector("pre code")
        assert "md.bold" in page.locator("pre code").last.inner_text()
    finally:
        page.close()


def test_sending_a_list_message_renders_list_items(chat_ui_url, browser) -> None:
    page = browser.new_page()
    try:
        page.goto(chat_ui_url, wait_until="networkidle")
        page.get_by_test_id("textbox").fill("give me a todo list")
        page.get_by_role("button", name="Send").click()
        page.wait_for_function("document.querySelectorAll('li').length >= 3")
        items = page.locator("li").all_inner_texts()
        assert items == ["review the PR", "run the tests", "ship it"]
    finally:
        page.close()


def test_sending_a_generic_message_renders_bold_and_italic(chat_ui_url, browser) -> None:
    page = browser.new_page()
    try:
        page.goto(chat_ui_url, wait_until="networkidle")
        page.get_by_test_id("textbox").fill("hello there")
        page.get_by_role("button", name="Send").click()
        page.wait_for_selector("text=Got it.")
        bot_bubble = page.get_by_test_id("bot").last
        assert bot_bubble.locator("strong", has_text="Got it.").count() == 1
        assert bot_bubble.locator("em").count() == 1
    finally:
        page.close()
