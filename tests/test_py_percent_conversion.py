from __future__ import annotations

import json

import pytest

import markdown as md


def test_markdown_py_percent_fixed_point_preserves_python_comments():
    source = (
        "# Demo\n\n"
        "説明です。\n\n"
        "~~~python\n"
        "# keep this comment\n"
        "value = 1\n"
        "text = \"# %% is not a marker inside a string\"\n"
        "~~~\n"
    )

    percent = md.markdown_to_py_percent(source)
    restored = md.py_percent_to_markdown(percent)

    assert "# keep this comment" in percent
    assert md.markdown_to_py_percent(restored) == percent


def test_py_percent_parser_uses_real_comment_tokens_for_markers():
    percent = (
        "# %%\n"
        "text = \"# %%\"\n"
        "# ordinary comment\n"
        "print(text)\n"
    )

    restored = md.py_percent_to_markdown(percent)

    assert 'text = "# %%"' in restored
    assert "# ordinary comment" in restored
    assert restored.count("~~~python") == 1


def test_py_percent_markdown_cell_round_trip():
    percent = (
        "# %% [markdown]\n"
        "# # Title\n"
        "#\n"
        "# 日本語 paragraph\n"
        "# %%\n"
        "print(\"ok\")\n"
    )

    markdown = md.py_percent_to_markdown(percent)

    assert markdown.startswith("# Title\n\n日本語 paragraph\n")
    assert md.markdown_to_py_percent(markdown) == percent


def test_py_percent_to_markdown_rejects_uncommented_markdown_payload():
    percent = "# %% [markdown]\nnot a comment\n"

    with pytest.raises(ValueError, match="must be a comment"):
        md.py_percent_to_markdown(percent)


def test_py_percent_to_markdown_requires_a_cell_marker():
    with pytest.raises(ValueError, match="No py:percent cell markers"):
        md.py_percent_to_markdown("print('plain python')\n")


def test_markdown_py_percent_ipynb_triangle_keeps_cell_semantics():
    source = (
        "# Notes\n\n"
        "before\n"
        "~~~python\n"
        "# comment survives\n"
        "x = 3\n"
        "~~~\n"
        "after\n"
    )

    baseline = json.loads(md.markdown_to_ipynb(source))
    percent = md.markdown_to_py_percent(source)
    via_percent = json.loads(md.markdown_to_ipynb(md.py_percent_to_markdown(percent)))

    assert via_percent["cells"] == baseline["cells"]
    assert via_percent["nbformat"] == baseline["nbformat"] == 4


def test_ipynb_markdown_py_percent_composition_is_stable():
    notebook = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# Title\n", "\n", "text\n"]},
            {
                "cell_type": "code",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": ["# keep\n", "print(1)\n"],
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    markdown = md.ipynb_to_markdown(notebook)
    percent = md.markdown_to_py_percent(markdown)
    restored_markdown = md.py_percent_to_markdown(percent)

    assert md.markdown_to_py_percent(restored_markdown) == percent
    assert "# keep" in percent
