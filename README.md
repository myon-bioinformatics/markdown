# markdown

stdlib だけで動く、関数提供に特化した Python Markdown ユーティリティ。

## GitHub About（推奨）

> Stdlib-only Markdown helpers for Python: read/write, section extraction, and HTML↔Markdown utilities for URLs and images. Functions only—no CLI; verified by tests.

## このリポジトリの立ち位置

ironmate などで使っていた `markdown.py` を、そのままのファイル名で pip 配布できるように育てるためのライブラリです。

- **標準ライブラリ前提** — 実行時依存を増やさず、できる範囲で機能を厚くする
- **関数提供に特化** — `main` / CLI エントリポイントは持たない。確認はテスト（`demos/*.py` の実処理もブラウザ不要のプレーンな関数呼び出しとして直接検証、任意で Streamlit / Gradio のフロント確認も可能）で行う
- **想定 API の方向性** — 既存の read / write / section 抽出に加え、HTML↔Markdown（URL・画像ファイルなど）の変換ヘルパを拡充していく
- **ascii_artist.py** — 本パッケージに同梱するか、別配置にするかは未決（要相談）

## Layout

| Path | Role |
| --- | --- |
| `markdown.py` | **The product** — vendored single module |
| `tests/` | pytest = correctness |
| `fixtures/` | Famous-README-inspired offline snippets + YAML/JSON/TOML + `benchmark/` (real, sourced Markdown) |
| `demos/gradio_app.py` | Optional: paste/upload → instant analysis. `analyze()` has zero UI deps — call it directly |
| `demos/streamlit_app.py` | Optional: sectioned headings/links/images/HTML/code view. `build_view()` has zero UI deps — call it directly |
| `demos/chat_ui_demo.py` | Optional: generic mock chat screen — assistant replies built with `markdown.py`'s generation helpers, rendered by Gradio's `Chatbot` |
| `demos/openai_compat_mock.py` | Optional: OpenAI-compatible chat completions server (stdlib only) so a real chat product can be pointed at `render_assistant_turn()`'s output instead of a real LLM — also issues one real OpenAI-style tool call for the MCP round-trip test below |
| `docs/antipatterns.md` | A running log of concrete ways a real chat product has broken the Docker/Playwright smoke tests in an actual CI run, with root cause and fix |
| `scripts/real_world_pages_report.py` | Builds the `real-world-pages` GitHub Actions workflow's Pages report: original vs. `html_to_markdown()`→`markdown_to_html()` round-trip, screenshotted via Playwright's own CLI, for every real HTML fixture in `fixtures/provenance.yaml` |

## Quick use

```python
import markdown as md

md.save_markdown("# Hello\n", "out.md")
sections = md.extract_sections(open("out.md", encoding="utf-8").read())
inv = md.inventory(open("README.md", encoding="utf-8").read())
print(md.html_image_to_markdown('<img src="a.png" alt="A" />'))
print(md.make_link("Docs", "https://example.com"))

# GitHub alert (also flavor="qiita" / "zenn" / "obsidian" / "gitlab")
print(md.alert("NOTE", "Useful information that users should know"))

# build Markdown from scratch
report = md.section(
    "Summary",
    [
        md.key_value_table({"mode": "train", "epochs": 10}),
        md.bullet_list(["loss down", "iou up"]),
        md.blockquote("keep the contract small"),
    ],
)
print(report)

# library-side HTML + CSS (no separate .css asset required)
html = "<style>" + md.default_stylesheet() + "</style>\n" + md.markdown_to_html(report)
print(html)

# thin Markdown ↔ Kramdown IAL (headings / paragraphs only)
print(md.with_attributes(md.heading("Intro"), id="intro", classes="hero"))
print(md.markdown_to_kramdown("# Title {#intro .hero}"))
```


## Lightweight HTML DOM helpers

`HtmlNode` is a small, stdlib-only normalized tree for conversion work. It is
**not** a browser DOM and does not claim HTML5 tree-construction fidelity.

- `parse_html_dom(html)` builds a root/element/text tree with lowercase tags.
- `dom_to_html(node)` serializes only the supported safe tag subset.
- `dom_to_markdown(node)` reuses the existing conservative HTML→Markdown
  contract; `<details><summary>` is preserved as the repository's
  `:::details` form.
- `markdown_to_dom(markdown)` converts through the existing
  `markdown_to_html()` subset and then parses the sanitized tree.

The boundary is intentionally conservative: `script` / `style` subtrees,
event attributes such as `onclick`, inline `style=`, and unsafe URL schemes
are dropped. Unknown tags degrade to transparent containers so safe text and
supported descendants remain available. Existing `html_to_markdown()` and
`markdown_to_html()` entry points are not rewritten around the DOM layer in
this first contract-focused step.


## Context helpers

The stdlib-only context helpers added in PR #12 are deterministic preparation
utilities, not a CommonMark parser or an LLM summarizer:

- extract_section selects one ATX heading and its nested children.
- strip_prose_keep_structure keeps headings, lists, blockquotes, thematic breaks,
  and fenced code while dropping ordinary prose lines.
- minify_markdown removes optional HTML comments and collapses excessive blank
  lines without converting Markdown.
- safe_truncate enforces a character limit and closes an open code fence when
  the limit leaves enough room.

Conversation-history compression and broader HTML conversion remain separate
future design topics. See docs/context_helpers.md for the exact contracts.

## Test / demo

```bash
pip install -r requirements-dev.txt
pytest

# optional frontends (only needed to see the actual UI — not to verify behavior)
pip install -r requirements-frontend.txt
python demos/gradio_app.py
streamlit run demos/streamlit_app.py
python demos/chat_ui_demo.py   # generic mock chat UI (gr.Chatbot)

# verify demo behavior without a browser or either frontend framework installed:
# analyze()/build_view() are plain functions, so a one-liner is enough.
python -c "import sys; sys.path.insert(0, 'demos'); import gradio_app; \
print(gradio_app.analyze('# Hi\n\n[x](https://example.com)\n'))"

# optional: verify each app's real wiring with no browser, no clicking, no JS —
# gradio_client / curl hit Gradio's own HTTP API directly; AppTest runs the
# Streamlit script headless; curl checks Streamlit's HTTP health + index.
pytest tests/frontend
```

Gradio's backend is a plain FastAPI app, so `tests/frontend/test_gradio_curl.py` drives it with
nothing but `curl` (POST to start a job, GET an SSE stream for the result) — no Python client
library needed, just what's already on any Ubuntu box. Streamlit's interactive reruns are a
stateful websocket protocol rather than a request/response API, so `AppTest` (not curl) is what
actually exercises its widgets; `test_streamlit_curl.py` uses `curl` for what *is* plain HTTP
there — the health endpoint and initial page. `tests/test_demo_logic.py` covers `analyze()` /
`build_view()` directly, with no frontend dependency installed at all.

CI runs **pytest + PyYAML** (and stdlib `tomllib` / `json`), which already covers `demos/*.py`'s
real logic via `tests/test_demo_logic.py` — no extra dependency installs needed. Gradio / Streamlit
themselves (the actual UI, not its behavior) — including the browser-free `tests/frontend` wiring
checks — stay optional (`workflow_dispatch` / local smoke).

`demos/chat_ui_demo.py` is the one demo in this repo with an actual chat screen
(a bubble-history `gr.Chatbot`, not tied to any specific product), so it's also
the one demo whose frontend tests click through the real rendered page.
`markdown.py`'s generation helpers only build the Markdown *text* — it's
Gradio's own `Chatbot` component that renders that text to HTML in the
browser. This repo's own `markdown_to_html()` now also renders simple GFM
pipe tables to `<table>` (see "Capability stance" below); the chat-screen
test still checks Gradio's DOM, while `tests/test_chat_ui_demo_logic.py`
checks the library HTML path. `tests/frontend/test_chat_ui_screen.py`
types a message, clicks Send, and asserts on the resulting DOM
(a real `<table>` with `<th>`/`<td>` rows, `<pre><code>`, `<li>`, `<strong>`/`<em>`)
via Playwright (`pip install -r requirements-frontend.txt && playwright install chromium`).
Its pure rendering logic (`render_assistant_turn` / `respond`, no gradio import
needed) is covered separately in `tests/test_chat_ui_demo_logic.py`.

Viewing rendered Markdown doesn't actually require a chat UI (or any app) at
all, though — `markdown_to_html()`'s output is just an HTML file, and
Playwright ships a CLI for exactly that: `python -m playwright screenshot`
and `python -m playwright pdf` render a `file://` URL with no server and no
`sync_playwright()` script, the same "reach for the tool's own CLI" approach
this repo already takes with curl for HTTP APIs.
`tests/frontend/test_markdown_html_playwright_cli.py` drives both against
this repo's own generated Markdown to confirm the HTML is real, renderable
output.

## Benchmark: how far does this get on real Markdown?

`tests/test_benchmark_commonmark.py`, `tests/test_benchmark_realworld.py`, and
`tests/test_benchmark_html_roundtrip.py` run real, published Markdown — not just this repo's own
README — through `markdown.py` and record, reproducibly, what works and what doesn't. The goal
isn't "pass everything" (this is explicitly not a full CommonMark/GFM engine — see Capability
stance below); it's knowing exactly where the edges are, and pinning that down so a real change
is a deliberate decision, not a silent regression.

Sources (full provenance — commit SHA, license, exact excerpted line ranges — in
[`fixtures/provenance.yaml`](fixtures/provenance.yaml)):

- **CommonMark spec** (`fixtures/benchmark/commonmark_examples.yaml`) — 13 of the spec's own 655
  numbered examples (spec version 0.31.2), covering headings, emphasis, nested emphasis, escaping,
  blockquotes, nested lists, fenced/inline code, horizontal rules, links, and two emphasis edge cases
- **GitHub Docs** (`fixtures/benchmark/github_docs_markdown.md`) — real excerpts from
  [github/docs](https://github.com/github/docs)'s own Markdown-writing documentation, covering
  headings, links, images, fenced code (including a fence nested inside a fence), nested lists,
  tables, task lists, autolinks, alerts, footnotes, and inline HTML
- **nodejs/node's `CONTRIBUTING.md`** (`fixtures/benchmark/contributing_example.md`) — a real OSS
  contributing guide, close to verbatim
- **axios/axios's `CHANGELOG.md`** (`fixtures/benchmark/changelog_example.md`) — the real first 400
  (of 1416) lines, for long-input stability with many headings/links/lists/version strings
- **とほほのWWW入門** (`fixtures/benchmark/tohoho_web_home.html`) — the real, live top page (not a git
  repo, so provenance is `fetched_at` + sha256 instead of a commit SHA): 1 `<h1>`, 24 `<h2>`, 263
  `<a href>`, `<header>`/`<aside>`/`<main>`/`<footer>` semantic wrappers, a `<form>`, and inline
  `<script>` ad blocks — a real, dense page for `html_to_markdown()` (the *other* direction), not
  just the small synthetic snippet `test_benchmark_html_roundtrip.py` used to rely on alone

Results, CommonMark spec examples:

| Construct | Classification |
| --- | --- |
| ATX headings, emphasis (basic), fenced code, inline code, horizontal rule, links | PASS |
| nested emphasis (`**foo *bar* baz**`) | DEGRADED — the inner `*bar*` parses, the outer `**` doesn't |
| nested lists | DEGRADED — flattens to one `<ul>`, no text lost |
| blockquotes | DEGRADED — consecutive `>` lines become `<blockquote><p>…</p></blockquote>`; inner ATX headings/lists/tables stay paragraph text; blank `>` lines split paragraphs |
| backslash escaping | FAIL — not implemented; `\*` stays literal instead of suppressing emphasis |
| emphasis edge cases (asymmetric delimiter runs, whitespace-adjacent delimiters) | FAIL |

Results, GitHub-flavored constructs found inside the real GitHub Docs excerpt:

| Construct | Classification |
| --- | --- |
| headings, links, images, fenced code (incl. fence-in-fence), inline code | PASS |
| nested lists | DEGRADED |
| tables | PASS — simple GFM pipe tables (header + `\| --- \|` delimiter) render as `<table>/<thead>/<th>/<tbody>/<td>`; cell text is escaped and reuses the inline renderer. Alignment colons are accepted, not emitted as attributes. Pipe rows without a delimiter stay paragraphs. |
| strikethrough (`~~text~~`) | PASS — renders as `<del>text</del>`; unmatched `~~` stays literal |
| task lists | PASS — `- [ ]` / `- [x]` / `- [X]` (also `*` / `+`) become `<li>` with a disabled checkbox; mixed with ordinary bullets in one `<ul>`. This fixture's Task lists section only shows the syntax in inline code, so it stays literal there. `1. [ ]` is not a task. |
| footnotes | PASS — live `[^id]` plus `[^id]:` definitions become superscript links and a trailing `<section class="footnotes">`. This fixture's Footnotes section only shows the syntax in a fenced example, so it stays code there. Undefined refs stay literal; duplicate ids: first definition wins. |
| autolinks | DEGRADED — `<https://…>` / `<http://…>` become `<a href>`; bare URLs stay literal. Arbitrary `<tag>` (including `<script>`) is escaped, not linked. |
| alerts (`> [!NOTE]`) | PASS — GitHub uppercase `[!NOTE]`/`[!TIP]`/`[!IMPORTANT]`/`[!WARNING]`/`[!CAUTION]` (no same-line title) render as `<aside class="markdown-alert">`. Qiita `:::note`, Zenn `:::message`, and Obsidian callouts are also supported. Ordinary `>` quotes render as `<blockquote>`; alerts still win when the opener is `[!TYPE]`. |
| inline HTML | UNSUPPORTED — escaped, not passed through |

```bash
pytest tests/test_benchmark_commonmark.py tests/test_benchmark_realworld.py tests/test_benchmark_html_roundtrip.py -v
```

All three run in the default `pytest` — no extra dependency installs. `test_benchmark_html_roundtrip.py`
is a separate, exploratory HTML → Markdown → HTML round trip; it's deliberately not part of the
PASS/DEGRADED/UNSUPPORTED/FAIL grading above.

Results, `html_to_markdown()` on the real とほほのWWW入門 page: every one of its 25 headings and 263
links survives as a real Markdown construct (`test_tohoho_headings_and_links_survive_html_to_markdown`),
and the round trip back to HTML keeps all of them too. `<header>`/`<aside>`/`<main>`/`<footer>` aren't
in `_HTMLToMarkdownParser`'s handled-tag list, so they contribute no Markdown syntax of their own, but
the real text they wrap still survives (same "unsupported tag, text not data" fallback as unhandled wrapper tags; simple ``<table>`` is now converted to GFM pipes).
`<script>` content is suppressed, not leaked, same as `<style>`.

## Real chat product smoke test (Open WebUI, in Docker)

Every other frontend test here either has nothing to click (`demos/gradio_app.py` /
`demos/streamlit_app.py`) or clicks through a mock chat screen this repo itself built
(`demos/chat_ui_demo.py`). `tests/real_chat_ui/test_openwebui_docker.py` goes one step further:
it drives a **real, unmodified Open WebUI**, running from its own published Docker image, and
verifies *that actual product* renders `markdown.py`-generated Markdown correctly — not a mock of
it.

`demos/openai_compat_mock.py` is a small stdlib-only OpenAI-compatible chat completions server
(`GET /v1/models`, `POST /v1/chat/completions`, streaming and non-streaming) that reuses
`chat_ui_demo.py`'s own `render_assistant_turn()` keyword logic, so Open WebUI's "model" reply is
the exact same deterministic Markdown the generic mock demo already uses — no real LLM, no network
call out. `docker/openwebui-smoke/docker-compose.yml` runs it (and mcp-toolcall-lab's mock MCP
server — see below) as compose services on the stack's own Docker network, addressed by service
name rather than routed back through the host — more reproducible than `host.docker.internal`
(see `docs/antipatterns.md`) and self-contained: one `docker compose up` starts everything, in the
right order, with no separate host-side mock processes to start yourself. Open WebUI itself runs
with `WEBUI_AUTH=False` (skips the signup/login screen entirely) and `OPENAI_API_BASE_URLS`/
`DEFAULT_MODELS` pre-pointed at the mock backend, so there's no interactive setup to automate.

```bash
git clone https://github.com/myon-bioinformatics/mcp-toolcall-lab mcp-toolcall-lab
docker compose -f docker/openwebui-smoke/docker-compose.yml up -d
# wait for http://127.0.0.1:3000/health
OPEN_WEBUI_BASE_URL=http://127.0.0.1:3000 MOCK_MCP_SERVER_NAME="Mock MCP (mcp-toolcall-lab)" \
  pytest tests/real_chat_ui/ -v
docker compose -f docker/openwebui-smoke/docker-compose.yml down -v
```

These tests skip cleanly (`OPEN_WEBUI_BASE_URL` unset) everywhere else, including the default
`pytest` run — they only run in the `real-chat-ui-smoke` GitHub Actions workflow
(`workflow_dispatch` only: a full container + browser run is too slow/heavy to gate every push or
PR, the same policy `frontend-smoke` already uses) or a manual local run as above. On a failure,
that workflow uploads a screenshot and the compose stack's container logs as artifacts.

### Triggering `real-chat-ui-smoke` without the "Run workflow" form

The workflow takes two optional `workflow_dispatch` inputs, so a chat message and a run label can
be supplied programmatically instead of clicking through the Actions tab's form each time:

- `message` — an extra chat message to send through the real UI; runs
  `test_openwebui_renders_a_custom_message_from_the_mock_backend` alongside the three fixed-content
  tests. Since the text is caller-supplied, that test only asserts *some* non-empty response
  rendered (not specific Markdown content — see the code comment for why).
- `run_label` — a free-text tag folded into the failure-artifact name, so results from several
  manual runs are easy to tell apart.

```bash
# gh CLI
gh workflow run real-chat-ui-smoke.yml -f message="show me a table" -f run_label="ad-hoc"
gh run list --workflow=real-chat-ui-smoke.yml --limit=1   # latest run + its conclusion

# REST API directly
curl -X POST -H "Authorization: Bearer $TOKEN" \
  https://api.github.com/repos/<owner>/<repo>/actions/workflows/real-chat-ui-smoke.yml/dispatches \
  -d '{"ref": "main", "inputs": {"message": "show me a table", "run_label": "ad-hoc"}}'
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/<owner>/<repo>/actions/workflows/real-chat-ui-smoke.yml/runs?per_page=1"
```

LibreChat is a planned second target here (see `docs`-equivalent notes in
[mcp-toolcall-lab](https://github.com/myon-bioinformatics/mcp-toolcall-lab)'s own LibreChat
integration for the parallel on that side) — not yet wired up in this repo.

### The real MCP tool-call round trip

`tests/real_chat_ui/test_openwebui_mcp_tool_call.py` goes further still: it registers a real MCP
tool server — [mcp-toolcall-lab](https://github.com/myon-bioinformatics/mcp-toolcall-lab)'s
`openwebui_mcp_mock.py`, run as this compose stack's own `mcp-mock` service rather than vendored
here, since that file is designed as a portable, drop-in single-file mock — as a
`TOOL_SERVER_CONNECTIONS` entry, clicks through Open WebUI's real per-chat "Tools" picker to enable
it (the same click path a real user takes, not a backend shortcut), sends a message that should
trigger a tool call, and verifies the tool's *actual* result renders in the chat.
`demos/openai_compat_mock.py`'s "model" recognizes one trigger phrase and issues a real
OpenAI-style `tool_calls` response referencing whichever tool name the request actually offered
(never hardcoded, since a tool-server-backed function name is prefixed by the caller); on the
follow-up request it unwraps the MCP result (which nests a second layer of JSON — confirmed by
probing the real `mcp` client SDK against the real mock server, not guessed) and renders it as a
Markdown table. This is exactly the round trip `docs/antipatterns.md` exists for — see there for
concrete failures a live run has actually produced.

The local-repro command above already covers this: cloning `mcp-toolcall-lab` as a subdirectory of
this repo's checkout and `docker compose up` are all that's needed — `mcp-mock` installs
`fastmcp` itself at container start, and `MOCK_MCP_SERVER_NAME` must match `docker-compose.yml`'s
`TOOL_SERVER_CONNECTIONS.info.name` exactly (already the case in the command above).

**[`docs/antipatterns.md`](docs/antipatterns.md)** is a running log of concrete ways a real chat
product has broken this setup in an actual `workflow_dispatch` run — not predicted failures, only
ones a live run produced, with the root cause traced to the product's own source. When the MCP
round trip above doesn't come back correctly, that's exactly the kind of failure the log exists to
capture.

## Capability stance

This is **not** a full CommonMark/GFM engine (see `SUPPORTED` / `UNSUPPORTED` in `markdown.py`, and
the benchmark above for what that looks like on real documents).
It shines at I/O, inventory, URL/image/HTML helpers, conservative conversions, and generating
Markdown from scratch (`heading`, `bold`/`italic`/`strikethrough`, `blockquote`, `alert`, `horizontal_rule`,
`bullet_list`/`numbered_list`/`task_item`/`task_list`, `inline_code`/`code_block`/`json_block`, `table`/`key_value_table`,
`md_table`/`md_kv` (`*args`-friendly, no list/dict pre-building needed), `status_line`,
`section`/`wrap_section`, `details`, `footnote`/`footnote_ref`) — all of which you can reason about.

`alert()` emits GitHub `> [!NOTE]` by default (`kind` is case-insensitive, emitted uppercase).
Pass `flavor="qiita"` for `:::note info|warn|alert`, `flavor="zenn"` for `:::message` /
`:::message alert`, `flavor="obsidian"` for lowercase callouts with optional `title=` / `fold=`,
or `flavor="gitlab"` for GitLab's lowercase five-kind form (optional `title=`). Unknown GitHub /
Qiita / Zenn / GitLab kinds raise `ValueError`. `markdown_to_html()` renders those blocks to a
shared `<aside class="markdown-alert" data-alert-flavor="…">` shape. Embed
`<style>{md.default_stylesheet()}</style>` (or `md.alert_stylesheet()`) next to
`markdown_to_html(...)` output — compact stdlib CSS, no separate `.css` file and
no external URLs. Ordinary `>` blockquotes render as `<blockquote>` (multi-line;
blank `>` lines split paragraphs). Simple GFM pipe tables from `table()` /
`key_value_table()` / `md_table()` round-trip through `markdown_to_html()` into
`<table>`. `~~text~~` becomes `<del>`. GFM task lists (`task_item()` /
`task_list()`, or hand-written `- [ ]` / `- [x]`) render as disabled
checkboxes. Angle-bracket `<https://…>` / `<http://…>` autolinks become
`<a href>` (bare URLs stay literal). `details(summary, body)` emits
Zenn-style `:::details` which `markdown_to_html()` turns into
`<details><summary>` (raw HTML `<details>` in Markdown stays escaped).
`[^id]` plus `[^id]:` definitions become superscript footnote links and
a `.footnotes` section. `html_to_markdown()` maps simple `<table>` trees
back to GFM pipes, `<del>` to `~~…~~`, and checkbox `<li><input>` to
`- [ ]` / `- [x]`. Heading / paragraph `id` / `class` become a trailing
Pandoc-style `{#id .class}`; `markdown_to_kramdown()` turns that into a
Kramdown block IAL (`{: #id .class key="value"}`), and
`kramdown_to_markdown()` strips known IAL back to plain Markdown
(attributes dropped). `ial()` / `with_attributes()` write those IAL
lines. Wikipedia infoboxes, Math, mermaid, Liquid `{% %}` / `{{ }}`,
YAML front matter, Jekyll includes / tags / baseurl, and full Kramdown
(extensions, math, TOC macros, span IAL) remain out of scope, as does
full CommonMark/GFM.

`code_block()`'s fence length is adaptive: plain content still gets a triple-backtick fence, but
content that itself contains a run of backticks (e.g. Markdown-about-Markdown, like a fenced example
inside a doc — see the GitHub Docs benchmark fixture above for a real one) gets a longer fence, just
enough to stay unambiguous, matching what CommonMark itself requires. Pass `fence_char="~"` for a
tilde fence instead. See `tests/test_adaptive_fence.py`.

## License

MIT
