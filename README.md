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

## Quick use

```python
import markdown as md

md.save_markdown("# Hello\n", "out.md")
sections = md.extract_sections(open("out.md", encoding="utf-8").read())
inv = md.inventory(open("README.md", encoding="utf-8").read())
print(md.html_image_to_markdown('<img src="a.png" alt="A" />'))
print(md.make_link("Docs", "https://example.com"))
```

## Test / demo

```bash
pip install -r requirements-dev.txt
pytest

# optional frontends
pip install -r requirements-frontend.txt
python demos/gradio_app.py
streamlit run demos/streamlit_app.py

# optional: browser-driven UI tests for both frontends (Playwright)
playwright install chromium
pytest tests/frontend
```

CI runs **pytest + PyYAML** (and stdlib `tomllib` / `json`). Gradio / Streamlit — including the
Playwright-driven `tests/frontend` UI checks that launch each app and click through it in a real
browser — stay optional (`workflow_dispatch` / local smoke).

## Capability stance

This is **not** a full CommonMark/GFM engine (see `SUPPORTED` / `UNSUPPORTED` in `markdown.py`).  
It shines at I/O, inventory, URL/image/HTML helpers, and conservative conversions you can reason about.

## License

MIT
