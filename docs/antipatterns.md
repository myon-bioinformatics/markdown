# Real chat UI smoke test: anti-patterns

A running log of concrete ways the `real-chat-ui-smoke` GitHub Actions workflow
(`.github/workflows/real-chat-ui-smoke.yml`) has actually failed against a real,
unmodified chat product in Docker -- not predicted failures, only ones a live
`workflow_dispatch` run produced. Each entry is a specific bug in *our* test
setup that a real product's own behavior exposed, plus the fix.

The point of keeping this here rather than only in a commit message: the same
handful of product behaviors (a first-run modal, an auth quirk, a selector
that only exists after some async load) tend to recur across every real chat
product this repo drives with Playwright, so a new entry here should be
useful before writing the next test, not just as a record after the fact.

## Format

Each entry: what we tried, what actually happened (with the concrete error),
the root cause traced to the product's own source, and the fix. Link the
GitHub Actions run that produced it.

---

## 1. Open WebUI's "What's New" changelog modal blocks `#chat-input`

- **Product / run**: Open WebUI, [run 35409468100](https://github.com/myon-bioinformatics/markdown/actions/runs/35409468100) (first live `workflow_dispatch` run after PR #11 merged)
- **What we tried**: `page.goto(OPEN_WEBUI_BASE_URL)`, wait for `#chat-input`, click it, type, press Enter.
- **What actually happened**: all 4 tests failed identically --
  `Locator.click: Timeout 30000ms exceeded`. Playwright's own retry log showed
  why: `#chat-input` resolved fine, but a `<div role="dialog" aria-modal="true"
  class="modal ...">` on top of it intercepted every click attempt for the
  full 30s window.
- **Root cause** (confirmed from Open WebUI's own source,
  `src/routes/(app)/+layout.svelte` and `ChangelogModal.svelte` at commit
  `0a7c158`): the admin account sees a "What's New" release-notes modal
  whenever `$settings.version != $config.version`. The `WEBUI_AUTH=False`
  auto-provisioned admin account this setup uses never has a persisted
  `settings.version`, so `$settings?.version !== $config.version` is true on
  *every single run*, every time -- this is not a flaky first-boot condition,
  it is the account's permanent state under this config.
- **Fix**: dismiss the modal before interacting with the chat input, the same
  way a real user would -- `Escape` closes the top-most modal
  (`common/Modal.svelte`'s own `handleKeyDown` checks `isTopModal()` and hides
  it). Implemented as `_dismiss_blocking_dialog()` in
  `tests/real_chat_ui/test_openwebui_docker.py`, called at the top of
  `_send_message()` so every test gets it for free.
- **Generalizable lesson**: any account state that is normally "seen once,
  then dismissed and remembered" (release notes, onboarding tours, cookie
  banners) will fire on *every* run against a fresh, non-persistent account --
  budget for dismissing it unconditionally rather than treating it as a
  one-time setup step.

## 2. The failure-screenshot fixture never actually took a screenshot

- **Product / run**: our own test harness, not Open WebUI --
  [run 35410172298](https://github.com/myon-bioinformatics/markdown/actions/runs/35410172298)
  (second live run, after fix #1 above; 3 of 4 tests also failed on real
  content timeouts in that same run -- a separate, not yet diagnosed issue,
  since this fixture bug meant no screenshot existed to debug it from).
- **What we tried**: `tests/real_chat_ui/conftest.py`'s `_screenshot_on_failure`
  autouse fixture was meant to save `test-results/<test name>.png` on any
  failure, so a live-run failure would be fast to debug from the uploaded
  artifact.
- **What actually happened**: the failure artifact was 272 bytes both times
  this ran for real (this run and the one before it) -- just the mock
  backend's log, no screenshot ever present, despite 3 real test failures.
- **Root cause**: the fixture read `page` via
  `request.node.funcargs.get("page")` instead of declaring it as a real
  fixture dependency. pytest instantiates autouse fixtures with no declared
  dependency *before* the fixtures a test explicitly requests, and tears
  them down in the reverse order -- so this fixture's post-`yield` code ran
  *after* the `page` fixture's own teardown had already called `page.close()`.
  `page.screenshot()` on an already-closed page raised, and the broad
  `except Exception: pass` swallowed it silently. Confirmed with a minimal
  standalone pytest reproduction (two dummy fixtures, one autouse without the
  dependency, one with it) before changing the real file.
- **Fix**: declare the dependency explicitly --
  `def _screenshot_on_failure(request, page):` -- which flips the teardown
  order so the screenshot is taken while the page is still open.
- **Generalizable lesson**: an autouse fixture that reaches for another
  fixture's value via `request.node.funcargs` instead of declaring it as a
  parameter gets the *value* but not pytest's ordering guarantee -- and
  teardown-order bugs like this fail silently instead of loudly whenever the
  reached-for resource is closed/invalidated by its own teardown, which a
  broad `except: pass` will hide indefinitely. Prefer the explicit
  dependency; if a broad except around cleanup code is truly necessary, log
  what it swallowed rather than passing silently.

## 3. The mock backend's SSE streams never signaled their own end

- **Product / run**: `demos/openai_compat_mock.py` (our own mock, not a real
  product) -- two live runs in a row,
  [run 35410172298](https://github.com/myon-bioinformatics/markdown/actions/runs/35410172298) and
  [run 35411574697](https://github.com/myon-bioinformatics/markdown/actions/runs/35411574697):
  every test after the first one in the job timed out waiting for content
  that was never going to arrive, while the very first streamed reply of the
  job always rendered correctly.
- **What we tried**: the mock's streaming (`"stream": true`) responses sent
  `Content-Type: text/event-stream` and `Connection: keep-alive`, wrote the
  SSE chunks, and returned -- the same shape as any small stdlib SSE mock.
- **What actually happened**: could not get a screenshot for this one --
  Azure Blob Storage, where GitHub Actions actually stores uploaded
  artifacts, is itself blocked by this sandbox's own egress policy (`curl`
  to `productionresultssa6.blob.core.windows.net` got a 403 at the proxy,
  confirmed against two different blob hosts across two runs) even after
  fixing entry 2's fixture bug and getting a real 73KB artifact uploaded.
  Diagnosed instead from what *was* readable here -- GitHub's own job-log API
  (plain text) -- and confirmed with a local reproduction using `httpx`
  (the same client library Open WebUI's backend actually uses, confirmed
  from its source) rather than staying with a guess: opened one
  `httpx.Client`, sent three sequential streaming requests to the mock
  over it. Against the buggy code, every single request timed out waiting
  for the stream to end (never just the first one) -- the same class of bug,
  demonstrated with a real client under our own control instead of only
  inferred from the live run's symptom.
- **Root cause**: an HTTP/1.1 response body's end is signaled by
  `Content-Length`, `Transfer-Encoding: chunked`, or the connection closing --
  nothing else. This response used none of the first two, so the *only* way
  for a client to know the body had ended was the server closing the
  connection -- which it never did (no `self.close_connection = True`, and
  `Connection: keep-alive` was sent besides). A client that fully drains the
  stream waiting for EOF hangs forever; this is a genuine protocol bug, not
  a client-specific quirk, so it isn't dependent on figuring out exactly how
  Open WebUI's own httpx-based SSE consumption managed to render the first
  reply anyway.
- **Fix**: send `Connection: close` and set `self.close_connection = True`
  after writing an SSE body, forcing a fresh connection for the next
  request rather than leaving the previous one in an ambiguous state.
  Factored into one `_send_sse()` helper so both streaming code paths (the
  plain reply and the tool-call response) get it. Re-ran the same `httpx`
  reproduction against the fixed code: all three sequential requests
  succeeded immediately.
- **Generalizable lesson**: a hand-rolled SSE server must pick one of
  `Content-Length` (impossible for a genuinely open-ended stream),
  `Transfer-Encoding: chunked`, or closing the connection -- there is no
  fourth option, and "the first request happened to work" is not evidence
  the framing is correct, since the very first request on a connection is
  the one case with no prior ambiguity to expose. When a live run's only
  failure evidence (a screenshot) turns out to be unreachable, treat that as
  a cue to reproduce with a tool actually under your control (a plain
  client script) rather than only re-reading the same job log for clues
  it doesn't contain.

<!--
## N. <short title>

- **Product / run**: <product>, [run <id>](<url>)
- **What we tried**: ...
- **What actually happened**: ... (quote the real error)
- **Root cause**: ... (traced to the product's own source/behavior, not guessed)
- **Fix**: ...
- **Generalizable lesson**: ...
-->
