from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import markdown as md

AUDIT_SCRIPT = ROOT / "scripts" / "converter_contract_audit.py"


def _load_audit():
    spec = importlib.util.spec_from_file_location("converter_contract_audit", AUDIT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_malformed_ancestor_close_balances_strong_like_dom_path() -> None:
    html = "<div><p>hello<strong> world</div>"

    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == "hello** world**\n"
    assert legacy == dom


def test_malformed_ancestor_close_balances_nested_inline_delimiters() -> None:
    html = "<div><p><strong>bold <em>and italic</div>"

    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == "**bold *and italic***\n"
    assert legacy == dom


def test_malformed_ancestor_close_balances_inline_code() -> None:
    html = "<div><p>use <code>x = 1</div>"

    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == "use `x = 1`\n"
    assert legacy == dom


def test_orphan_endtag_does_not_invent_markup() -> None:
    assert md.html_to_markdown("<p>hello</strong></p>") == "hello\n"


def test_malformed_case_is_no_longer_a_converter_audit_divergence() -> None:
    audit = _load_audit()
    report = audit.collect_report()

    assert "html:malformed" not in report["divergent_case_ids"]
