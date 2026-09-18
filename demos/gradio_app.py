"""Gradio front-end for manual Markdown helper checks.

Optional dependency: ``pip install -r requirements-frontend.txt``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def analyze(text: str, uploaded_path: str | None = None) -> tuple[str, str, str, str]:
    source = text or ""
    if uploaded_path:
        loaded = md.read_markdown(uploaded_path)
        if loaded["success"]:
            source = loaded["content"]
    inv = md.inventory(source)
    headings = "\n".join(
        f"{'#' * row['level']} {row['title']}" for row in inv["headings"]
    ) or "(none)"
    links = "\n".join(f"- {row['text']}: {row['url']}" for row in inv["links"]) or "(none)"
    images = "\n".join(f"- {row['alt']}: {row['url']}" for row in inv["images"]) or "(none)"
    summary = json.dumps(
        {
            "heading_count": inv["heading_count"],
            "link_count": inv["link_count"],
            "image_count": inv["image_count"],
            "code_block_count": inv["code_block_count"],
            "raw_html_count": inv["raw_html_count"],
            "urls": inv["urls"],
        },
        indent=2,
    )
    return headings, links, images, summary


def build_app():
    import gradio as gr

    with gr.Blocks(title="markdown.py lab") as demo:
        gr.Markdown("# markdown.py lab\nPaste Markdown or upload a `.md` file.")
        with gr.Row():
            text = gr.Textbox(lines=18, label="Markdown")
            file = gr.File(label="Upload .md", file_types=[".md", ".markdown", ".txt"])
        btn = gr.Button("Analyze")
        headings = gr.Textbox(label="Headings", lines=8)
        links = gr.Textbox(label="Links", lines=8)
        images = gr.Textbox(label="Images", lines=8)
        summary = gr.Code(label="Inventory summary (JSON)", language="json")

        def _run(text_value, file_obj):
            path = file_obj.name if file_obj is not None else None
            return analyze(text_value or "", path)

        btn.click(_run, inputs=[text, file], outputs=[headings, links, images, summary], api_name="analyze")
    return demo


if __name__ == "__main__":
    # Importable without launching; demos are for humans, not library entry points.
    build_app().launch()
