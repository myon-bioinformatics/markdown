"""A generic mock chat UI that renders assistant replies with markdown.py.

Not modeled on any single product — the text-box + send-button + scrolling
bubble-history layout here is the common shape shared by ChatGPT, Claude.ai,
Open WebUI, LibreChat, LobeChat, and effectively every other chat UI. What
they all also share: assistant replies are rendered as Markdown. This demo
exercises exactly that path using this repo's own generation helpers
(``section``, ``table``, ``code_block``, ``bullet_list``, ``bold``/``italic``)
instead of a real LLM — deterministic and offline, matching every other demo
in this repo.

Optional dependency: ``pip install -r requirements-frontend.txt``
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

Turn = dict  # {"role": "user" | "assistant", "content": str}


def render_assistant_turn(user_text: str) -> str:
    """Build one assistant reply as Markdown, using ``user_text`` to pick a shape.

    No LLM involved: a few keyword rules stand in for "the model decided to
    reply with a table/code/list," which lets this stay a pure, dependency-free
    function testable with a one-liner (see ``tests/test_demo_logic.py``) — the
    same pattern ``demos/gradio_app.py``'s ``analyze()`` already uses.
    """
    lowered = user_text.lower()

    if "table" in lowered:
        return md.section(
            "Results",
            [
                md.table(
                    ["metric", "value"],
                    [["loss", "0.041"], ["iou", "0.87"], ["epochs", "12"]],
                )
            ],
        )

    if "code" in lowered:
        return md.section(
            "Snippet",
            [md.code_block("import markdown as md\nprint(md.bold('hi'))\n", lang="python")],
        )

    if "list" in lowered or "todo" in lowered:
        return md.section(
            "Next steps",
            [md.bullet_list(["review the PR", "run the tests", "ship it"])],
        )

    return md.section(
        "Reply",
        [f"{md.bold('Got it.')} {md.italic('Ask for a table, code, or list to see more.')}\n"],
    )


def respond(user_text: str, history: list[Turn]) -> tuple[str, list[Turn]]:
    """Append one user/assistant exchange to ``history``; returns ("", new_history).

    The empty string is the cleared value for the input textbox — matching the
    signature Gradio's ``Chatbot`` examples use for a submit handler.
    """
    history = list(history)
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": render_assistant_turn(user_text)})
    return "", history


SAMPLE_CONVERSATION: list[Turn] = [
    {"role": "user", "content": "Show me a results table"},
    {"role": "assistant", "content": render_assistant_turn("Show me a results table")},
]


def build_app():
    import gradio as gr

    with gr.Blocks(title="markdown.py chat UI demo") as demo:
        gr.Markdown(
            "# markdown.py chat UI demo\n"
            "A generic mock chat screen — ask about a **table**, **code**, or **list** "
            "and the reply is built with `markdown.py`'s generation helpers."
        )
        chatbot = gr.Chatbot(value=list(SAMPLE_CONVERSATION), label="Chat")
        msg = gr.Textbox(label="Message", placeholder="Try: 'show me a table'")
        send = gr.Button("Send")

        send.click(respond, inputs=[msg, chatbot], outputs=[msg, chatbot])
        msg.submit(respond, inputs=[msg, chatbot], outputs=[msg, chatbot])
    return demo


if __name__ != "__main__":
    pass
else:
    build_app().launch()
