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
| `demos/openai_compat_mock.py` | Optional: OpenAI-compatible chat completions server (stdlib only) so a real chat product can be pointed at `render_assistant_turn()`'s output instead of a real LLM |

## Quick use

```python
import markdown as md

md.save_markdown("# Hello\n", "out.md")
sections = md.extract_sections(open("out.md", encoding="utf-8").read())
inv = md.inventory(open("README.md", encoding="utf-8").read())
print(md.html_image_to_markdown('<img src="a.png" alt="A" />'))
print(md.make_link("Docs", "https://example.com"))

# build Markdown from scratch
report = md.section(
    "Summary",
    [
        md.key_value_table({"mode": "train", "epochs": 10}),
        md.bullet_list(["loss down", "iou up"]),
    ],
)
print(report)
```

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
browser, tables included (see "Capability stance" below: this repo's own
`markdown_to_html()` does not render GFM tables, by design — it's a
different, much smaller converter than Gradio's). `tests/frontend/test_chat_ui_screen.py`
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

Results, CommonMark spec examples:

| Construct | Classification |
| --- | --- |
| ATX headings, emphasis (basic), fenced code, inline code, horizontal rule, links | PASS |
| nested emphasis (`**foo *bar* baz**`) | DEGRADED — the inner `*bar*` parses, the outer `**` doesn't |
| nested lists | DEGRADED — flattens to one `<ul>`, no text lost |
| blockquotes | UNSUPPORTED — escapes and flattens to a plain paragraph, same fallback as tables |
| backslash escaping | FAIL — not implemented; `\*` stays literal instead of suppressing emphasis |
| emphasis edge cases (asymmetric delimiter runs, whitespace-adjacent delimiters) | FAIL |

Results, GitHub-flavored constructs found inside the real GitHub Docs excerpt:

| Construct | Classification |
| --- | --- |
| headings, links, images, fenced code (incl. fence-in-fence), inline code | PASS |
| nested lists | DEGRADED |
| tables, task lists, footnotes | UNSUPPORTED (matches the pre-existing `unsupported_examples` note) |
| autolinks (`<url>`, bare URLs) | UNSUPPORTED |
| alerts (`> [!NOTE]`) | UNSUPPORTED — built on the same unsupported blockquote syntax |
| inline HTML | UNSUPPORTED — escaped, not passed through |

```bash
pytest tests/test_benchmark_commonmark.py tests/test_benchmark_realworld.py tests/test_benchmark_html_roundtrip.py -v
```

All three run in the default `pytest` — no extra dependency installs. `test_benchmark_html_roundtrip.py`
is a separate, exploratory HTML → Markdown → HTML round trip; it's deliberately not part of the
PASS/DEGRADED/UNSUPPORTED/FAIL grading above.

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
call out. `docker/openwebui-smoke/docker-compose.yml` runs Open WebUI with `WEBUI_AUTH=False`
(skips the signup/login screen entirely) and `OPENAI_API_BASE_URLS`/`DEFAULT_MODELS` pre-pointed at
that mock backend, so there's no interactive setup to automate.

```bash
python demos/openai_compat_mock.py &
docker compose -f docker/openwebui-smoke/docker-compose.yml up -d
# wait for http://127.0.0.1:3000/health
OPEN_WEBUI_BASE_URL=http://127.0.0.1:3000 pytest tests/real_chat_ui/test_openwebui_docker.py -v
docker compose -f docker/openwebui-smoke/docker-compose.yml down -v
```

These tests skip cleanly (`OPEN_WEBUI_BASE_URL` unset) everywhere else, including the default
`pytest` run — they only run in the `real-chat-ui-smoke` GitHub Actions workflow
(`workflow_dispatch` only: a full container + browser run is too slow/heavy to gate every push or
PR, the same policy `frontend-smoke` already uses) or a manual local run as above. On a failure,
that workflow uploads a screenshot and the container logs as artifacts.

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

## Capability stance

This is **not** a full CommonMark/GFM engine (see `SUPPORTED` / `UNSUPPORTED` in `markdown.py`, and
the benchmark above for what that looks like on real documents).
It shines at I/O, inventory, URL/image/HTML helpers, conservative conversions, and generating
Markdown from scratch (`heading`, `bold`/`italic`/`strikethrough`, `blockquote`, `horizontal_rule`,
`bullet_list`/`numbered_list`, `inline_code`/`code_block`/`json_block`, `table`/`key_value_table`,
`md_table`/`md_kv` (`*args`-friendly, no list/dict pre-building needed), `status_line`,
`section`/`wrap_section`) — all of which you can reason about.

`code_block()`'s fence length is adaptive: plain content still gets a triple-backtick fence, but
content that itself contains a run of backticks (e.g. Markdown-about-Markdown, like a fenced example
inside a doc — see the GitHub Docs benchmark fixture above for a real one) gets a longer fence, just
enough to stay unambiguous, matching what CommonMark itself requires. Pass `fence_char="~"` for a
tilde fence instead. See `tests/test_adaptive_fence.py`.

## License

MIT
