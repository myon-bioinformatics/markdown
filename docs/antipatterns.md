# Markdown anti-pattern catalog

This document records recurring design traps, test failures, and integration
mistakes observed while keeping `markdown.py` a stdlib-only, single-file
library.

It has two layers:

1. **Stable anti-pattern IDs** for reusable design and maintenance rules.
2. **Observed incidents** from real CI / Docker / Playwright runs, kept as
   concrete evidence with root cause and fix.

The rule is simple: when a failure is likely to recur, give it a stable ID and
add a regression or contract test where practical. Do not leave important
behavior only in a PR comment or commit message.

## Stable catalog

| ID | Anti-pattern | Why it is harmful | Preferred contract |
| --- | --- | --- | --- |
| `DUPLICATE_IMPLEMENTATION` | `markdown.py`, a package copy, or a vendored copy evolve independently | Fixes drift and behavior diverges silently | `markdown.py` is the sole implementation artifact; package/vendor forms wrap or copy it |
| `PYPI_NAME_EQUALS_IMPORT_ASSUMPTION` | Treating the PyPI distribution name as if it must rename the implementation module | Creates needless second implementations or import churn | `md-market` may be the distribution name while the actual module remains `markdown.py` |
| `NON_STDLIB_RUNTIME_DEPENDENCY` | Core helpers require PyYAML, BeautifulSoup, a browser, or another package | Breaks copy-one-file use and vendoring | Core runtime stays stdlib-only; optional demos/tests may use extra packages |
| `REGEX_AS_FULL_MARKDOWN_PARSER` | Growing one regex into a CommonMark/GFM parser | Edge cases become impossible to reason about | Use narrow regexes/scanners for declared subsets; explicitly mark unsupported syntax |
| `DUPLICATED_URL_POLICY` | Each converter implements its own URL scheme rules | Security and conversion behavior diverge between paths | Reuse the shared URL sanitization contract for conversion paths |
| `SILENT_LOSSY_ROUNDTRIP` | A lossy transform is treated as exact round-trip without documentation | Expected information loss looks like a regression, or real regressions get hidden | Record expected-lossy cases separately from unexplained divergence |
| `DOM_PARITY_BY_INTERMEDIATE_SHAPE` | Comparing intermediate DOM/HTML shape instead of final Markdown contract | Harmless internal differences are misclassified as bugs | Judge parity by declared final-output contract unless intermediate shape itself is public |
| `DOM_FIRST_WITH_THIN_CORPUS` | Switching architecture after synthetic tests or one real page look clean | Evidence is too narrow to justify compatibility claims | Track real-world case count and expand corpus before broad cutover |
| `EMPTY_OUTPUT_AS_NEWLINE` | Empty/suppressed input returns a lone newline | Empty-value contracts become inconsistent and downstream checks misbehave | Empty output is exactly `""`; non-empty normalized output follows its own newline contract |
| `UNDECLARED_LOSSINESS` | Converter drops attributes, comments, whitespace, footnote syntax, etc. without saying so | Users cannot distinguish deliberate normalization from bugs | Declare source/target subset and lossiness in docs/tests |
| `REIMPLEMENT_SHARED_SCANNER` | New helpers each invent their own fence/code-context detection | Code blocks and inline code get handled inconsistently | Reuse the shared scanner/masking helpers for code-context decisions |
| `EXPORT_REORDER_CHURN` | Feature PRs reorder the whole `__all__` list | Parallel PRs conflict for no functional reason | Add exports adjacent to functional peers; avoid repository-wide reordering |
| `VENDORED_SNAPSHOT_DRIFT` | A consumer's copied `markdown.py` changes without provenance or sync discipline | Vendored behavior no longer matches upstream | Treat this repo as source of truth and refresh reviewed snapshots intentionally |
| `SUBSTRING_ONLY_ASSERTION` | Integration tests only check that expected text appears somewhere | Structurally wrong output can still pass | Assert parsed structure/DOM/records when structure matters |
| `STALE_ELEMENT_HANDLE_WAIT` | Playwright polls a captured element while the framework replaces that node | Wait can time out although visible DOM is already correct | Re-query selectors during polling when node identity is unstable |
| `SILENT_CLEANUP_EXCEPTION` | Cleanup/diagnostic code uses broad `except: pass` | The evidence needed to debug the original failure disappears | Preserve fixture ordering and log swallowed cleanup failures |
| `HTTP11_SSE_WITHOUT_END_SIGNAL` | Hand-written SSE uses HTTP/1.1 without length/chunking/connection close | Clients hang waiting for a body that never terminates | Use chunking or close the connection explicitly |
| `FRAMEWORK_WRAPPER_ASSUMPTION` | Code assumes a low-level SDK result shape survives unchanged through a larger product | Middleware envelopes break parsing unexpectedly | Observe and normalize the actual end-to-end shape |
| `STANDARD_DOM_ASSUMPTION` | Tests assume rendered Markdown always becomes conventional HTML such as `<pre><code>` | Real products may mount editors/components instead | Inspect the actual product DOM before choosing selectors |

## Contract rules derived from the catalog

- Keep `markdown.py` as the only implementation source of truth.
- Keep runtime behavior stdlib-only and usable by copying one file.
- Prefer explicit supported/unsupported subsets over accidental partial parsing.
- Centralize shared policies such as URL safety and code-context scanning.
- Separate **expected lossiness** from unexplained divergence in audits.
- Expand real-world fixtures before making architecture-wide compatibility claims.
- When a CI failure reveals a reusable lesson, add both documentation and a
  regression/contract test where practical.

---

# Observed real chat / CI incidents

The following entries are the original live-failure log from
`real-chat-ui-smoke` and related Docker/Playwright runs. They remain here
because they are concrete evidence behind several stable IDs above.

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

## 4. Open WebUI wraps a tool's result in a `{"results": [...]}` envelope

- **Product / run**: Open WebUI --
  [run 35412247498](https://github.com/myon-bioinformatics/markdown/actions/runs/35412247498)
  (first run where the MCP round trip actually completed end to end, after
  fixing entry 3's SSE bug).
- **What we tried**: `demos/openai_compat_mock.py`'s `_tool_result_records()`
  unwrapped one specific nesting -- a JSON string of MCP content blocks
  (`[{"type": "text", "text": "<json>"}]`) -- based on probing the real
  `mcp` client SDK's `MCPClient.call_tool()` return value directly. That's
  what the *low-level* SDK call returns; it is not what actually arrived in
  the tool message's `content` once real Open WebUI middleware (not our own
  probe script) built it.
- **What actually happened**: the round trip completed and the Playwright
  assertions on substring content even happened to pass (`has_text` matches
  substrings, and the raw Python `repr()` of the result list still
  contained "14109"/"Yokohama"/"Kanagawa" as text) -- but the rendered table
  had one column named `results` with a single row holding the whole
  result as one `str(list_of_dicts)`-formatted cell, not real
  `code`/`name`/`prefecture` columns. Caught by actually reading the mock's
  own new request-logging line in the job log, not by the test failing.
- **Root cause**: Open WebUI's middleware wraps a tool's return value in its
  own `{"results": [...]}` envelope before handing it to the model as the
  tool message's `content` -- one level *above* the MCP content-block layer,
  and present with or without that layer underneath it (both shapes were
  seen for real). A probe against the SDK in isolation only shows what that
  one layer returns, not what the full stack wraps it in afterward.
- **Fix**: after unwrapping the MCP content-block layer (if present), also
  check for a `results`/`result` key holding a list and use that.
- **Generalizable lesson**: probing one library's return value in isolation
  tells you that library's contract, not the shape a larger framework wraps
  around it before the data reaches you -- a passing assertion is not proof
  of correct handling when the assertion only checks substrings; watch the
  actual parsed structure too (here, the request-logging line that was
  already added for a different reason turned out to be what caught this).

## 5. Open WebUI renders code blocks with CodeMirror, never `<pre><code>`

- **Product / run**: Open WebUI --
  [run 35417244601](https://github.com/myon-bioinformatics/markdown/actions/runs/35417244601),
  and the run before it once the SSE bug (entry 3) stopped masking it.
- **What we tried**: `container.locator("pre code")` to find a rendered
  fenced code block, the same selector any CommonMark-to-HTML renderer
  would produce.
- **What actually happened**: permanent timeout, every run, even after the
  mock's reply content was confirmed correct. Root-caused (not guessed) by
  adding a DOM-dump-to-stdout diagnostic to conftest.py and reading the
  actual failing job's captured output: the response container held a full
  CodeMirror 6 editor instance (`class="cm-editor"`, `.cm-content`,
  `.cm-line` divs with syntax-highlighting `<span>`s), not a `<pre><code>`
  element anywhere.
- **Root cause**: Open WebUI renders fenced code blocks as a live,
  interactive CodeMirror editor (it has Copy/Save/Run buttons and is
  presumably editable) instead of static `<pre><code>` markup. This isn't a
  timing issue or a race -- the element the test was waiting for was never
  going to exist, in any amount of time.
- **Fix**: assert against `.cm-content` (CodeMirror's own class, stable
  across whichever exact code-block feature set Open WebUI has) instead of
  `pre code`.
- **Generalizable lesson**: a chat product that supports "Run" or "Save" on
  a code block is not just running a Markdown-to-HTML renderer over the
  reply -- it may be mounting a real editor component instead of the plain
  markup a spec-compliant CommonMark renderer would produce. Verify the
  actual DOM before assuming standard tags for anything the product treats
  as more than static content.

## 6. `wait_for_function` against a captured `element_handle()` can hang forever on live content

- **Product / run**: our own test (`test_openwebui_docker.py`), not Open
  WebUI -- [run 35417244601](https://github.com/myon-bioinformatics/markdown/actions/runs/35417244601).
- **What we tried**: for the list test,
  `page.wait_for_function("(el) => el.querySelectorAll('li').length >= 3", arg=container.element_handle(), timeout=30_000)`
  -- poll a single captured element for enough `<li>` children to appear.
- **What actually happened**: permanent timeout, even though the DOM dump
  added for entry 5 showed the *finished* response already had all three
  `<li>` items rendered correctly (`<ul dir="auto"><li class="text-start ">…`)
  once the test gave up and the fixture inspected the live page afterward.
  The content was right; the wait condition never saw it.
- **Root cause**: `element_handle()` returns a handle bound to one specific
  DOM node, captured once at call time. If Open WebUI's Svelte rendering
  replaces that node while the response streams in (rather than mutating
  it in place) -- plausible given the DOM dump also caught it mid-render at
  least once (`<h2>Snippet</h2>` present but nothing streamed under it
  yet) -- every later evaluation against the old handle keeps checking the
  *original, now-detached* node, frozen at whatever child count it had the
  moment it was replaced. The condition can look permanently false while
  the visible, current DOM already satisfies it.
- **Fix**: poll via a fresh `document.querySelectorAll(...)` lookup inside
  the injected function itself (re-run on every poll tick) instead of a
  captured handle -- `_wait_for_last_response()` in
  `test_openwebui_docker.py`.
- **Generalizable lesson**: `element_handle()` is a snapshot, not a live
  reference -- safe for a condition checked once, but the wrong tool for a
  `wait_for_function` poll against content a framework might still be
  replacing wholesale rather than mutating. Prefer re-querying by selector
  string inside the polled function itself when the target node's identity
  isn't guaranteed stable across the wait.

<!--
## N. <short title>

- **Product / run**: <product>, [run <id>](<url>)
- **What we tried**: ...
- **What actually happened**: ... (quote the real error)
- **Root cause**: ... (traced to the product's own source/behavior, not guessed)
- **Fix**: ...
- **Generalizable lesson**: ...
-->
