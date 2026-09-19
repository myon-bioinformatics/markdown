"""Save a screenshot for any failed test in this directory, so a first-run
selector mismatch against the real Open WebUI container is fast to debug
from the CI artifact instead of only a traceback."""

from __future__ import annotations

from pathlib import Path

import pytest

RESULTS_DIR = Path(__file__).resolve().parents[2] / "test-results"


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def _screenshot_on_failure(request, page):
    # Depending on `page` explicitly (rather than only fetching it from
    # request.node.funcargs) matters for teardown *order*: an autouse
    # fixture with no declared dependency on `page` is torn down before it
    # (autouse fixtures are set up first, so torn down last-in-first-out --
    # after `page`'s own fixture has already closed it), so page.screenshot()
    # below would silently hit a closed page every time and do nothing. This
    # was confirmed live: two failed CI runs each produced a failure artifact
    # with no screenshot in it. Declaring `page` here forces the opposite
    # order -- this fixture tears down (and takes its screenshot) before
    # `page` closes.
    yield
    failed = getattr(request.node, "rep_call", None)
    failed = failed is not None and failed.failed
    if not failed:
        return
    RESULTS_DIR.mkdir(exist_ok=True)
    safe_name = request.node.name.replace("/", "_")
    try:
        page.screenshot(path=str(RESULTS_DIR / f"{safe_name}.png"), full_page=True)
    except Exception:
        pass

    # Also print the actual rendered DOM to stdout, not just a screenshot:
    # pytest captures stdout and shows it in a failed test's own section, so
    # this reaches the job log directly, no artifact download required --
    # the only channel this sandbox could reliably read from during earlier
    # diagnosis (Azure Blob Storage, where GitHub Actions actually stores
    # uploaded artifacts, is blocked by its own egress policy).
    try:
        containers = page.locator("#response-content-container").all()
        print(f"[dom-dump] #response-content-container count={len(containers)}")
        if containers:
            html = containers[-1].evaluate("el => el.outerHTML")
            print(f"[dom-dump] last container outerHTML (first 4000 chars):\n{html[:4000]}")
    except Exception as exc:
        print(f"[dom-dump] failed: {exc!r}")
