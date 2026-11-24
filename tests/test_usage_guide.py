"""The published guide must cover the public callable and data surface."""
from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _output_texts(blocks):
    for block in blocks:
        if block["type"] == "output":
            yield block["text"]
        yield from _output_texts(block.get("blocks", []))


def _documented_cli_and_api():
    page = json.loads((ROOT / "docs/guide.page.json").read_text(encoding="utf-8"))
    guide = next(block for block in page["blocks"] if block.get("id") == "guide")
    cli = next(tab for tab in guide["tabs"] if tab["label"].endswith("機能一覧"))
    api = next(tab for tab in guide["tabs"] if tab["label"].endswith("Python API 全一覧"))
    commands = {
        command
        for sample in _output_texts(cli["blocks"])
        for command in re.findall(r"^.*python markdown\.py ([a-z-]+)\b", sample, re.MULTILINE)
    }
    symbols = [
        line.split(" — ", 1)[0]
        for card in _output_texts(api["blocks"])
        for line in card.splitlines()
    ]
    return commands, symbols


def test_published_guide_covers_public_python_symbols_and_cli_commands():
    source = ast.parse((ROOT / "markdown.py").read_text(encoding="utf-8"))
    exports = next(
        ast.literal_eval(node.value)
        for node in source.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    main = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == "_main")
    operations = next(
        ast.literal_eval(keyword.value)
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "operation"
        for keyword in node.keywords if keyword.arg == "choices"
    )
    guide_commands, guide_symbols = _documented_cli_and_api()
    assert Counter(guide_symbols) == Counter(exports)
    assert guide_commands == set(operations)
