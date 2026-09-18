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
| `fixtures/` | Famous-README-inspired offline snippets + YAML/JSON/TOML |
| `demos/gradio_app.py` | Optional: paste/upload → instant analysis. `analyze()` has zero UI deps — call it directly |
| `demos/streamlit_app.py` | Optional: sectioned headings/links/images/HTML/code view. `build_view()` has zero UI deps — call it directly |
| `demos/chat_ui_demo.py` | Optional: generic mock chat screen — assistant replies built with `markdown.py`'s generation helpers, rendered by Gradio's `Chatbot` |

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

## Capability stance

This is **not** a full CommonMark/GFM engine (see `SUPPORTED` / `UNSUPPORTED` in `markdown.py`).  
It shines at I/O, inventory, URL/image/HTML helpers, conservative conversions, and generating
Markdown from scratch (`heading`, `bold`/`italic`/`strikethrough`, `blockquote`, `horizontal_rule`,
`bullet_list`/`numbered_list`, `inline_code`/`code_block`/`json_block`, `table`/`key_value_table`,
`md_table`/`md_kv` (`*args`-friendly, no list/dict pre-building needed), `status_line`,
`section`/`wrap_section`) — all of which you can reason about.

## License

MIT
