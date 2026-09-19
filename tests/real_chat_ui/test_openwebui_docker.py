"""Real Open WebUI, in a real Docker container, rendering markdown.py's own output.

Every other frontend test in this repo either avoids clicking (there's nothing
to look at) or clicks through a generic mock chat screen this repo itself
built (``demos/chat_ui_demo.py``). This one is different: it drives the
actual Open WebUI product, running unmodified from its own published Docker
image, pointed at ``demos/openai_compat_mock.py`` instead of a real LLM so the
"model's" reply is deterministic Markdown built by this repo's own
``markdown.py`` helpers (the same ``render_assistant_turn()`` logic
``chat_ui_demo.py`` uses). The question this answers that the generic mock
demo test can't: does a real, unmodified chat product's own Markdown
renderer actually turn that output into the HTML it's supposed to?

Only runs with ``OPEN_WEBUI_BASE_URL`` set, which only the CI workflow
(``.github/workflows/real-chat-ui-smoke.yml``, ``workflow_dispatch`` only) or
a manual local run of ``docker/openwebui-smoke/docker-compose.yml`` sets --
never in the default ``pytest`` run, since it needs a real running container.

Selectors here were derived by reading Open WebUI's own frontend source
(open-webui/open-webui, commit 0a7c158) rather than verified against a live
instance locally -- this sandbox's network policy blocks pulling the
ghcr.io image. The GitHub Actions run is the first live verification; on a
selector mismatch, the workflow uploads a screenshot and the container logs
as artifacts to make iterating on that fast.
"""

from __future__ import annotations

import os
import re

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

OPEN_WEBUI_BASE_URL = os.environ.get("OPEN_WEBUI_BASE_URL")

pytestmark = pytest.mark.skipif(
    not OPEN_WEBUI_BASE_URL,
    reason="OPEN_WEBUI_BASE_URL not set -- only the real-chat-ui-smoke workflow "
    "(workflow_dispatch) or a manual docker/openwebui-smoke run sets this",
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
    """Open WebUI shows the admin a "What's New" changelog modal
    (ChangelogModal.svelte) whenever $settings.version != $config.version --
    true on every run here, since the WEBUI_AUTH=False auto-provisioned admin
    account never persists a stored settings.version across container
    restarts. It sits on top of #chat-input and intercepts clicks, so it must
    be dismissed first -- the same way a user would, via Escape (the close
    button has no stable selector; Escape is common/Modal.svelte's own
    top-most-dialog handler)."""
    dialog = page.locator('div[role="dialog"][aria-modal="true"]')
    if dialog.count():
        page.keyboard.press("Escape")
        dialog.last.wait_for(state="hidden", timeout=5_000)


def _send_message(page, text: str) -> None:
    """Type into Open WebUI's chat input and submit -- it's a rich-text
    (contenteditable) editor by default, not a plain <textarea>, so this
    clicks and types rather than using .fill()."""
    _dismiss_blocking_dialog(page)
    chat_input = page.locator("#chat-input")
    chat_input.click()
    page.keyboard.type(text)
    page.keyboard.press("Enter")


def _wait_for_last_response(page, predicate_js: str, timeout: int = 30_000) -> None:
    """Poll a condition against the *live*, re-queried last
    #response-content-container element, not a captured element_handle().

    element_handle() snapshots one specific DOM node. If Open WebUI's own
    Svelte rendering replaces that node while streaming completes (rather
    than mutating it in place), the handle goes stale: further evaluations
    against it freeze at whatever child state existed at capture time, so a
    condition like "has >= 3 <li>" can look permanently false even once the
    live DOM (a new node occupying the same visual spot) already satisfies
    it -- confirmed live: docs/antipatterns.md. predicate_js is a JS
    arrow-function body string receiving that live element as `el`.
    """
    page.wait_for_function(
        f"""() => {{
            const containers = document.querySelectorAll('#response-content-container');
            if (!containers.length) return false;
            const el = containers[containers.length - 1];
            return ({predicate_js})(el);
        }}""",
        timeout=timeout,
    )


def test_openwebui_renders_markdown_table_from_the_mock_backend(page) -> None:
    page.goto(OPEN_WEBUI_BASE_URL, wait_until="networkidle")

    # WEBUI_AUTH=False auto-signs in; DEFAULT_MODELS pre-selects the mock
    # model -- there is no login form or model picker to drive here.
    page.wait_for_selector("#chat-input", timeout=30_000)

    _send_message(page, "show me a table")

    container = page.locator("#response-content-container").last
    container.locator("table").wait_for(timeout=30_000)

    table = container.locator("table")
    assert table.locator("th", has_text=re.compile("metric", re.I)).count() >= 1
    assert table.locator("td", has_text="loss").count() >= 1
    assert table.locator("td", has_text="0.041").count() >= 1


def test_openwebui_renders_markdown_code_block_from_the_mock_backend(page) -> None:
    page.goto(OPEN_WEBUI_BASE_URL, wait_until="networkidle")
    page.wait_for_selector("#chat-input", timeout=30_000)

    _send_message(page, "show me some code")

    # Not "pre code": Open WebUI renders code blocks with a live CodeMirror 6
    # editor (.cm-content/.cm-line), not plain <pre><code> -- confirmed from
    # the actual rendered DOM (see docs/antipatterns.md), not assumed.
    container = page.locator("#response-content-container").last
    container.locator(".cm-content").wait_for(timeout=30_000)
    assert "md.bold" in container.locator(".cm-content").last.inner_text()


def test_openwebui_renders_markdown_list_from_the_mock_backend(page) -> None:
    page.goto(OPEN_WEBUI_BASE_URL, wait_until="networkidle")
    page.wait_for_selector("#chat-input", timeout=30_000)

    _send_message(page, "give me a todo list")

    _wait_for_last_response(page, "el => el.querySelectorAll('li').length >= 3")
    items = page.locator("#response-content-container").last.locator("li").all_inner_texts()
    assert [item.strip() for item in items] == ["review the PR", "run the tests", "ship it"]


CUSTOM_CHAT_MESSAGE = os.environ.get("CUSTOM_CHAT_MESSAGE", "").strip()


@pytest.mark.skipif(
    not CUSTOM_CHAT_MESSAGE,
    reason="CUSTOM_CHAT_MESSAGE not set -- set the real-chat-ui-smoke workflow's "
    "'message' input (or export CUSTOM_CHAT_MESSAGE locally) to exercise an "
    "arbitrary chat message instead of only the three fixed-content cases above",
)
def test_openwebui_renders_a_custom_message_from_the_mock_backend(page) -> None:
    """Unlike the fixed-content tests above, the message here is caller-supplied
    (workflow_dispatch input or a local env var), so it can't assert specific
    Markdown content -- chat_ui_demo.render_assistant_turn() picks its reply from
    the keywords in the message, falling back to an echo. This only confirms the
    round trip works end to end: a real, unmodified Open WebUI actually renders
    *some* non-empty response to that message."""
    page.goto(OPEN_WEBUI_BASE_URL, wait_until="networkidle")
    page.wait_for_selector("#chat-input", timeout=30_000)

    _send_message(page, CUSTOM_CHAT_MESSAGE)

    _wait_for_last_response(page, "el => el.innerText.trim().length > 0")
    assert page.locator("#response-content-container").last.inner_text().strip()
