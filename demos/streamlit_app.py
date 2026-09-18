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

DEFAULT_FIXTURE = ROOT / "fixtures" / "vscode_readme_snippet.md"


def build_view(content: str) -> dict[str, object]:
    """Compute everything the UI displays, with no Streamlit dependency.

    This is the part of the app that is actually worth testing; keeping it
    free of ``streamlit`` imports means it can be called directly from a
    plain function call / one-liner (no server, no browser) in tests or at
    the command line, e.g.::

        python -c "import sys; sys.path.insert(0, 'demos'); import streamlit_app as s; \\
            print(s.build_view(open('README.md').read())['heading_count'])"
    """
    inv = md.inventory(content)
    return {
        "heading_count": inv["heading_count"],
        "link_count": inv["link_count"],
        "image_count": inv["image_count"],
        "code_block_count": inv["code_block_count"],
        "raw_html_count": inv["raw_html_count"],
        "headings": inv["headings"],
        "links": inv["links"],
        "images": inv["images"],
        "code_blocks": inv["code_blocks"],
        "raw_html": inv["raw_html"],
        "html_preview": md.markdown_to_html(content),
    }


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="markdown.py inspector", layout="wide")
    st.title("markdown.py inspector")
    st.caption("Sectioned view of headings / links / images / HTML / code blocks")

    default = DEFAULT_FIXTURE.read_text(encoding="utf-8")
    uploaded = st.file_uploader("Upload Markdown", type=["md", "markdown", "txt"])
    if uploaded is not None:
        content = uploaded.read().decode("utf-8")
    else:
        content = st.text_area("Markdown source", value=default, height=280)

    view = build_view(content)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Headings", view["heading_count"])
    c2.metric("Links", view["link_count"])
    c3.metric("Images", view["image_count"])
    c4.metric("Code", view["code_block_count"])
    c5.metric("Raw HTML", view["raw_html_count"])

    tab_h, tab_l, tab_i, tab_c, tab_html = st.tabs(
        ["Headings", "Links", "Images", "Code blocks", "HTML"]
    )
    with tab_h:
        st.table(view["headings"])
    with tab_l:
        st.table(view["links"])
    with tab_i:
        st.table(view["images"])
    with tab_c:
        for idx, block in enumerate(view["code_blocks"]):
            st.subheader(f"Block {idx + 1} ({block['language'] or 'plain'})")
            st.code(block["code"], language=block["language"] or None)
    with tab_html:
        st.table(view["raw_html"])

    st.subheader("Conservative HTML preview")
    st.code(view["html_preview"], language="html")


if __name__ == "__main__":
    # ``streamlit run demos/streamlit_app.py`` executes this file as __main__,
    # so this guard both launches the real UI and keeps a plain `import
    # streamlit_app` (e.g. from a test) free of side effects / a streamlit
    # dependency, matching demos/gradio_app.py's own guard below.
    main()
