# markdown

stdlib だけで動く、関数提供に特化した Python Markdown ユーティリティ。

## GitHub About（推奨）

> Stdlib-only Markdown helpers for Python: read/write, section extraction, and HTML↔Markdown utilities for URLs and images. Functions only—no CLI; verified by tests.

## このリポジトリの立ち位置

ironmate などで使っていた `markdown.py` を、そのままのファイル名で pip 配布できるように育てるためのライブラリです。

- **標準ライブラリ前提** — 実行時依存を増やさず、できる範囲で機能を厚くする
- **関数提供に特化** — `main` / CLI エントリポイントは持たない。確認はテスト（および任意で Streamlit / Gradio のフロント確認）で行う
- **想定 API の方向性** — 既存の read / write / section 抽出に加え、HTML↔Markdown（URL・画像ファイルなど）の変換ヘルパを拡充していく
- **ascii_artist.py** — 本パッケージに同梱するか、別配置にするかは未決（要相談）

## Layout

| Path | Role |
| --- | --- |
| `markdown.py` | **The product** — vendored single module |
| `tests/` | pytest = correctness |
| `fixtures/` | Famous-README-inspired offline snippets + YAML/JSON/TOML |
| `demos/gradio_app.py` | Optional: paste/upload → instant analysis |
| `demos/streamlit_app.py` | Optional: sectioned headings/links/images/HTML/code view |
| `demos/chat_ui_demo.py` | Optional: generic mock chat screen — assistant replies rendered with `markdown.py`'s generation helpers |

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

# optional frontends
pip install -r requirements-frontend.txt
python demos/gradio_app.py
streamlit run demos/streamlit_app.py
python demos/chat_ui_demo.py   # generic mock chat UI (gr.Chatbot)
```

CI runs **pytest + PyYAML** (and stdlib `tomllib` / `json`). Gradio / Streamlit stay optional (`workflow_dispatch` / local smoke).

`demos/chat_ui_demo.py` is the one demo in this repo with an actual chat screen
(a bubble-history `gr.Chatbot`, not tied to any specific product), so it's also
the one demo whose frontend tests click through the real rendered page —
`tests/frontend/test_chat_ui_screen.py` types a message, clicks Send, and
asserts on the resulting HTML (`<table>`, `<pre><code>`, `<li>`, `<strong>`/`<em>`)
via Playwright (`pip install -r requirements-frontend.txt && playwright install chromium`).
Its pure rendering logic (`render_assistant_turn` / `respond`, no gradio import
needed) is covered separately in `tests/test_chat_ui_demo_logic.py`.

## Capability stance

This is **not** a full CommonMark/GFM engine (see `SUPPORTED` / `UNSUPPORTED` in `markdown.py`).  
It shines at I/O, inventory, URL/image/HTML helpers, conservative conversions, and generating
Markdown from scratch (`heading`, `bold`/`italic`/`strikethrough`, `blockquote`, `horizontal_rule`,
`bullet_list`/`numbered_list`, `inline_code`/`code_block`/`json_block`, `table`/`key_value_table`,
`md_table`/`md_kv` (`*args`-friendly, no list/dict pre-building needed), `status_line`,
`section`/`wrap_section`) — all of which you can reason about.

## License

MIT
