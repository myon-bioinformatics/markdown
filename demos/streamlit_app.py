"""Streamlit front-end for sectioned Markdown inspection.

Optional dependency: ``pip install -r requirements-frontend.txt``

Run: ``streamlit run demos/streamlit_app.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="markdown.py inspector", layout="wide")
    st.title("markdown.py inspector")
    st.caption("Sectioned view of headings / links / images / HTML / code blocks")

    default = (ROOT / "fixtures" / "vscode_readme_snippet.md").read_text(encoding="utf-8")
    uploaded = st.file_uploader("Upload Markdown", type=["md", "markdown", "txt"])
    if uploaded is not None:
        content = uploaded.read().decode("utf-8")
    else:
        content = st.text_area("Markdown source", value=default, height=280)

    inv = md.inventory(content)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Headings", inv["heading_count"])
    c2.metric("Links", inv["link_count"])
    c3.metric("Images", inv["image_count"])
    c4.metric("Code", inv["code_block_count"])
    c5.metric("Raw HTML", inv["raw_html_count"])

    tab_h, tab_l, tab_i, tab_c, tab_html = st.tabs(
        ["Headings", "Links", "Images", "Code blocks", "HTML"]
    )
    with tab_h:
        st.table(inv["headings"])
    with tab_l:
        st.table(inv["links"])
    with tab_i:
        st.table(inv["images"])
    with tab_c:
        for idx, block in enumerate(inv["code_blocks"]):
            st.subheader(f"Block {idx + 1} ({block['language'] or 'plain'})")
            st.code(block["code"], language=block["language"] or None)
    with tab_html:
        st.table(inv["raw_html"])

    st.subheader("Conservative HTML preview")
    st.code(md.markdown_to_html(content), language="html")


# Streamlit executes the script top-down; keep library import free of side effects
# beyond calling main when run as the Streamlit target.
main()
