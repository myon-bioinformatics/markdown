from __future__ import annotations

import os
import socket

import pytest


@pytest.fixture()
def free_port() -> int:
    """A free TCP port on localhost for a demo server to bind to."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def browser():
    """A shared Chromium browser instance for the frontend UI tests.

    Honors ``PLAYWRIGHT_CHROMIUM_EXECUTABLE`` to point at a pre-installed
    browser binary when the Playwright pip package's expected revision
    doesn't match what's already on disk (e.g. some sandboxes); CI normally
    runs ``playwright install chromium`` first and doesn't need this.
    """
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    executable_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None
    with sync_playwright() as p:
        launched = p.chromium.launch(executable_path=executable_path)
        yield launched
        launched.close()
