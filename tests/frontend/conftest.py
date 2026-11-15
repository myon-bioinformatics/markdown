"""Shared frontend fixtures: the demos import path, a free port, a server wait and Chromium."""
from __future__ import annotations

import os, socket, sys, time, urllib.error, urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# The demo apps live in demos/ and import markdown from the repository root.
for path in (str(ROOT), str(ROOT / "demos")):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture()
def free_port() -> int:
    """A free TCP port on localhost for a demo server to bind to."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def wait_until_up():
    """``wait(url, name)``: poll a launched demo server until it answers (30 s at most)."""
    def wait(url: str, name: str, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(url, timeout=1)
                return
            except (urllib.error.URLError, ConnectionError) as exc:
                last_error = exc
                time.sleep(0.2)
        raise RuntimeError(f"{name} app did not start in time: {last_error}")
    return wait


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
