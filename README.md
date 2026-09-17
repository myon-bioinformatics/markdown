# markdown

**Single-file, stdlib-only Markdown helpers for Python.**  
Copy `markdown.py` into your project (ironmate など) — no PyPI name clash with the popular `Markdown` parser, no runtime dependencies.

生成AIや他リポジトリから参照・ベンダー配置される前提の「最強の1ファイル」を目指しています。CLI / `main` は持たず、関数提供に特化します。

## GitHub About

> Single-file, stdlib-only Markdown helpers for Python: I/O, structure extraction, and HTML↔Markdown utilities. Functions only—no CLI; verified by tests.

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
```

CI runs **pytest + PyYAML** (and stdlib `tomllib` / `json`). Gradio / Streamlit stay optional (`workflow_dispatch` / local smoke).

## Capability stance

This is **not** a full CommonMark/GFM engine (see `SUPPORTED` / `UNSUPPORTED` in `markdown.py`).  
It shines at I/O, inventory, URL/image/HTML helpers, and conservative conversions you can reason about.

`ascii_artist.py` is **out of scope** for this single file unless we later decide otherwise.

## License

MIT
