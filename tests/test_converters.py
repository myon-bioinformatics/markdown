"""🔁 Converters: case selection, contract audit, integration scaffold, parity report, notebooks, py:percent, structured adapters and snapshots, system formats, table data, LLM I/O and reference generators."""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import io
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
import markdown as md


# ═══ · converter case selection ══════════════════════════════════════════════════════════════════════════
# Case selection happens before conversion and preserves evaluation scope.

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name', ['converter_parity_report', 'converter_contract_audit'])
def test_list_never_reads_fixtures_or_converts(name, monkeypatch, capsys):
    module = load(name)
    def forbidden(*args, **kwargs):
        raise AssertionError('list must not read or convert')
    monkeypatch.setattr(Path, 'read_text', forbidden)
    monkeypatch.setattr(module.md, 'html_to_markdown', forbidden)
    assert module.main(['--case', 'html:basic*', '--list']) == 0
    assert json.loads(capsys.readouterr().out) == {'cases': ['html:basic_blocks']}


@pytest.mark.parametrize('name', ['converter_parity_report', 'converter_contract_audit'])
def test_subset_is_explicit_and_preserves_per_case_results(name):
    module = load(name)
    whole = module.collect_report()
    subset = module.collect_report(patterns=('html:basic*', 'html:basic*', 'html:table'), exclude=('table',))
    expected = [c for c in whole['cases'] if c['id'] == 'basic_blocks']
    if name.endswith('audit'):
        expected = [c for c in expected if c['kind'] == 'html']
    assert subset['cases'] == expected
    assert subset['case_count'] == 1 and subset['selection']['scope'] == 'selected_cases'
    assert subset['selection']['selected'] == 1
    assert 'selection' not in whole
    if name.endswith('report'):
        assert subset['decision_hint'] == 'selected_cases_only'


def test_excluded_markdown_and_cycles_are_not_converted(monkeypatch):
    module = load('converter_contract_audit')
    def forbidden(*args, **kwargs):
        raise AssertionError('excluded converters must not run')
    monkeypatch.setattr(module, '_markdown_record', forbidden)
    monkeypatch.setattr(module, '_structured_cycle_record', forbidden)
    result = module.collect_report(patterns=('html:basic_blocks',))
    assert result['case_count'] == 1 and result['structured_cycle_count'] == 0


@pytest.mark.parametrize('name', ['converter_parity_report', 'converter_contract_audit'])
def test_invalid_empty_or_mixed_modes_never_write(tmp_path, name):
    out = tmp_path / 'result.json'
    script = ROOT / 'scripts' / (name + '.py')
    for options in (['--case', 'missing'], ['--case', ''], ['--list']):
        result = subprocess.run([sys.executable, '-S', str(script), '--out', str(out)] + options,
                                cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 2 and result.stdout == ''
        assert not out.exists()
    result = subprocess.run([sys.executable, '-S', str(script), '--case', 'html:basic_blocks', '--list'],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['cases'] == ['html:basic_blocks']


# ═══ · converter contract audit ══════════════════════════════════════════════════════════════════════════

SCRIPT = ROOT / "scripts" / "converter_contract_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("converter_contract_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_converter_contract_audit_is_deterministic():
    audit = _load_module()
    assert audit.collect_report() == audit.collect_report()


def test_converter_contract_audit_covers_core_html_categories():
    audit = _load_module()
    expected = {
        "basic_blocks",
        "links_images",
        "mixed_lists",
        "table",
        "details",
        "task",
        "attributes",
        "malformed",
        "unicode",
        "unsafe_url",
        "empty",
    }
    assert expected <= set(audit.HTML_CASES)


def test_converter_contract_audit_covers_core_markdown_categories():
    audit = _load_module()
    expected = {
        "basic_blocks",
        "links_images",
        "mixed_lists",
        "table",
        "details",
        "task",
        "blockquote",
        "footnote",
        "attributes",
        "unicode",
        "empty",
    }
    assert expected <= set(audit.MARKDOWN_CASES)


def test_converter_contract_audit_reports_real_world_html():
    audit = _load_module()
    report = audit.collect_report()

    assert report["schema_version"] == 3
    assert report["case_count"] == len(report["cases"])
    assert (
        report["case_count"]
        == report["stable_case_count"]
        + report["expected_lossy_case_count"]
        + report["divergent_case_count"]
    )
    assert report["real_world_html_count"] >= 1
    assert report["raw_divergent_case_ids"] == [
        f'{case["kind"]}:{case["id"]}' for case in report["cases"]
        if not case["all_checks_pass"]
    ]
    assert report["divergent_case_ids"] == [
        f'{case["kind"]}:{case["id"]}' for case in report["cases"]
        if case["classification"] == "divergent"
    ]
    assert len(report["raw_divergent_case_ids"]) == len(
        set(report["raw_divergent_case_ids"])
    )


def test_converter_contract_audit_keeps_divergence_observational():
    audit = _load_module()
    report = audit.collect_report()

    assert "not automatically a bug" in report["note"].lower()
    for case in report["cases"]:
        assert set(case["checks"])
        assert case["all_checks_pass"] == all(case["checks"].values())
        assert case["classification"] in {"stable", "expected_lossy", "divergent"}


def test_blockquote_is_no_longer_a_converter_audit_divergence():
    audit = _load_module()
    report = audit.collect_report()

    assert "markdown:blockquote" not in report["divergent_case_ids"]


def test_mixed_lists_are_no_longer_converter_audit_divergences():
    audit = _load_module()
    report = audit.collect_report()

    assert "html:mixed_lists" not in report["divergent_case_ids"]
    assert "markdown:mixed_lists" not in report["divergent_case_ids"]


def test_footnote_is_classified_as_expected_lossy():
    audit = _load_module()
    report = audit.collect_report()

    assert "markdown:footnote" in report["raw_divergent_case_ids"]
    assert "markdown:footnote" in report["expected_lossy_case_ids"]
    assert "markdown:footnote" not in report["divergent_case_ids"]

    footnote = next(
        case for case in report["cases"]
        if case["kind"] == "markdown" and case["id"] == "footnote"
    )
    assert footnote["classification"] == "expected_lossy"
    assert "[^id]" in footnote["expected_loss_reason"]


def test_conversion_graph_distinguishes_prose_and_structured_markdown():
    audit = _load_module()
    graph = audit.collect_report()["conversion_graph"]

    assert "markdown_prose" in graph["nodes"]
    assert "markdown_structured_v1" in graph["nodes"]
    assert "not that arbitrary inputs round-trip" in graph["note"]

    edge_ids = {edge["id"] for edge in graph["edges"]}
    assert {
        "html_to_markdown_prose",
        "markdown_prose_to_html",
        "ini_to_markdown_structured_v1",
        "markdown_structured_v1_to_ini",
        "toml_to_markdown_structured_v1",
        "markdown_structured_v1_to_toml",
        "dotenv_to_markdown_structured_v1",
        "markdown_structured_v1_to_dotenv",
    } <= edge_ids
    assert all(edge["domain"] for edge in graph["edges"])


def test_conversion_graph_reports_reachability_without_crossing_carriers():
    audit = _load_module()
    graph = audit.collect_report()["conversion_graph"]
    pairs = {(route["source"], route["target"]) for route in graph["routes"]}

    assert ("html", "dom") in pairs
    assert ("ini", "toml") in pairs
    assert ("dotenv", "ini") in pairs
    assert ("html", "toml") not in pairs
    assert ("ini", "html") not in pairs

    if audit.md.toml_reader() is None:
        assert ("toml", "ini") not in pairs
    else:
        assert ("toml", "ini") in pairs


def test_structured_cycles_are_stable_on_supported_python():
    audit = _load_module()
    report = audit.collect_report()
    expected_ids = {case["id"] for case in audit.STRUCTURED_CYCLE_CASES}

    if audit.md.toml_reader() is None:
        assert report["structured_cycle_count"] == 0
        assert set(report["structured_cycle_unavailable_ids"]) == expected_ids
        return

    assert report["structured_cycle_count"] == len(expected_ids)
    assert report["structured_cycle_stable_count"] == len(expected_ids)
    assert report["structured_cycle_divergent_count"] == 0
    assert report["structured_cycle_divergent_ids"] == []
    assert report["structured_cycle_unavailable_ids"] == []
    assert {cycle["id"] for cycle in report["structured_cycles"]} == expected_ids
    for cycle in report["structured_cycles"]:
        assert cycle["carrier"] == "markdown_structured_v1"
        assert cycle["classification"] == "stable"
        assert cycle["all_checks_pass"]
        assert all(cycle["checks"].values())


def test_structured_cycles_cover_cross_format_paths():
    audit = _load_module()
    pairs = {
        (case["source_format"], case["via_format"])
        for case in audit.STRUCTURED_CYCLE_CASES
    }
    assert {
        ("ini", "toml"),
        ("dotenv", "toml"),
        ("toml", "ini"),
        ("toml", "dotenv"),
    } <= pairs


# ═══ · converter integration scaffold ════════════════════════════════════════════════════════════════════

PARITY_CASES = {
    "heading_and_paragraph": "<h1>Title</h1><p>Hello <strong>world</strong>.</p>",
    "links_and_images": (
        '<p><a href="https://example.com">docs</a> '
        '<img src="/img.png" alt="pic"></p>'
    ),
    "mixed_lists": "<ul><li>one</li><li><ol><li>nested</li></ol></li></ul>",
    "table": (
        "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
        "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    ),
    "task": '<ul><li><input type="checkbox" checked disabled> done</li></ul>',
    "unicode": "<p>日本語 <strong>世界</strong> café</p>",
    "unsafe_link_sanitization": '<p><a href="javascript:alert(1)">click</a></p>',
}


KNOWN_DOM_LEGACY_GAPS = {}


def test_public_html_to_markdown_is_a_compatibility_wrapper():
    for html in [*PARITY_CASES.values(), *KNOWN_DOM_LEGACY_GAPS.values()]:
        assert md.html_to_markdown(html) == md._html_to_markdown_impl(html)


def test_dom_and_legacy_paths_match_for_supported_parity_cases():
    for name, html in PARITY_CASES.items():
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert dom == legacy, name


def test_known_dom_legacy_gaps_are_explicit_and_stable():
    observed = {}
    for name, html in KNOWN_DOM_LEGACY_GAPS.items():
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        if legacy != dom:
            observed[name] = (legacy, dom)

    assert set(observed) == set(KNOWN_DOM_LEGACY_GAPS)


def test_dom_path_does_not_call_public_html_to_markdown(monkeypatch):
    def fail_public_wrapper(_html: str) -> str:
        raise AssertionError("dom_to_markdown must not call public html_to_markdown")

    monkeypatch.setattr(md, "html_to_markdown", fail_public_wrapper)

    assert md.dom_to_markdown(md.parse_html_dom("<p>Hello</p>")) == "Hello\n"

    details = md.dom_to_markdown(
        md.parse_html_dom(
            "<details><summary>More</summary><p>Body <strong>text</strong>.</p></details>"
        )
    )
    assert details.startswith(":::details More\n")
    assert "Body **text**." in details


URL_SAFETY_CASES = [
    ('<a href="javascript:alert(1)">click</a>', "click\n"),
    ('<a href="JavaScript:alert(1)">click</a>', "click\n"),
    ('<a href="javascript\x00:alert(1)">click</a>', "click\n"),
    ('<a href="java\tscript:alert(1)">click</a>', "click\n"),
    ('<a href="java\nscript:alert(1)">click</a>', "click\n"),
    ('<a href="data:text/html,boom">click</a>', "click\n"),
    ('<a href="vbscript:msgbox(1)">click</a>', "click\n"),
    ('<a href="https://example.com/x">click</a>', "[click](https://example.com/x)\n"),
    ('<a href="mailto:test@example.com">mail</a>', "[mail](mailto:test@example.com)\n"),
    ('<a href="../docs/page.html">docs</a>', "[docs](../docs/page.html)\n"),
    ('<a href="example.com:8080/path">host</a>', "[host](//example.com:8080/path)\n"),
    ('<img src="javascript:alert(1)" alt="pic">', "pic\n"),
    ('<img src="data:text/html,boom" alt="pic">', "pic\n"),
    ('<img src="/img.png" alt="pic">', "![pic](/img.png)\n"),
]


def test_legacy_html_url_safety_matches_dom_final_markdown():
    for html, expected in URL_SAFETY_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == expected, html
        assert dom == expected, html


def test_rejected_url_targets_never_emit_empty_markdown_targets():
    samples = [
        '<a href="javascript:alert(1)">click</a>',
        '<img src="javascript:alert(1)" alt="pic">',
    ]
    for html in samples:
        result = md.html_to_markdown(html)
        assert "]()" not in result
        assert "![](" not in result


EMPTY_OUTPUT_CASES = [
    "",
    "   ",
    "<script>alert(1)</script>",
    "<style>body{display:none}</style>",
    '<a href="javascript:x"></a>',
    '<img src="javascript:x" alt="">',
]


def test_empty_html_to_markdown_normalizes_to_empty_string():
    for html in EMPTY_OUTPUT_CASES:
        assert md.html_to_markdown(html) == "", html


def test_empty_output_matches_dom_path():
    for html in EMPTY_OUTPUT_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == dom == "", html


def test_non_empty_html_to_markdown_keeps_single_trailing_newline():
    samples = [
        ("<p>Hello</p>", "Hello\n"),
        ('<a href="https://example.com">x</a>', "[x](https://example.com)\n"),
        ('<img src="/x.png" alt="pic">', "![pic](/x.png)\n"),
    ]
    for html, expected in samples:
        assert md.html_to_markdown(html) == expected


DETAILS_PARITY_CASES = [
    (
        "<details><summary>More</summary><p>Body <em>text</em>.</p></details>",
        ":::details More\nBody *text*.\n:::\n",
    ),
    (
        "<details><p>Body only</p></details>",
        ":::details Details\nBody only\n:::\n",
    ),
    (
        "<details><summary></summary></details>",
        ":::details Details\n:::\n",
    ),
    (
        "<p>Before</p><details><summary>More</summary><p>Body</p></details><p>After</p>",
        "Before\n\n:::details More\nBody\n:::\n\nAfter\n",
    ),
    (
        "<details><div><summary>Nested</summary></div><p>Body</p></details>",
        ":::details Details\nNested\n\nBody\n:::\n",
    ),
]


def test_details_html_to_markdown_matches_dom_contract():
    for html, expected in DETAILS_PARITY_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == expected, html
        assert dom == expected, html


COMMENT_WHITESPACE_PARITY_CASES = [
    ("<p>A <!-- comment --> B</p>", "A B\n"),
    ("<p>A<!-- comment --> B</p>", "A B\n"),
    ("<p>A <!-- comment -->B</p>", "A B\n"),
]


def test_comment_boundaries_do_not_duplicate_collapsed_whitespace():
    for html, expected in COMMENT_WHITESPACE_PARITY_CASES:
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        assert legacy == expected, html
        assert dom == expected, html


def test_details_inside_table_cell_stays_flat_and_keeps_table_shape():
    html = (
        "<table><tr><th>kind</th><th>value</th></tr>"
        "<tr><td>x</td><td><details><summary>More</summary><p>Body</p></details></td></tr>"
        "</table>"
    )
    legacy = md.html_to_markdown(html)
    dom = md.dom_to_markdown(md.parse_html_dom(html))

    assert legacy == dom
    assert ":::details" not in legacy
    assert "| kind | value |" in legacy
    assert "| x | More Body |" in legacy


# ═══ · converter parity report ═══════════════════════════════════════════════════════════════════════════

CONVERTER_PARITY_REPORT_SCRIPT = ROOT / "scripts" / "converter_parity_report.py"


def _load_report_module():
    spec = importlib.util.spec_from_file_location("converter_parity_report", CONVERTER_PARITY_REPORT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_converter_parity_report_is_deterministic_and_covers_real_html():
    report_module = _load_report_module()
    first = report_module.collect_report()
    second = report_module.collect_report()

    assert first == second
    assert first["schema_version"] == 2
    assert first["case_count"] >= len(report_module.SYNTHETIC_CASES) + 1
    assert first["case_count"] == first["match_count"] + first["mismatch_count"]
    assert first["mismatch_ids"] == [
        case["id"] for case in first["cases"] if not case["equal"]
    ]
    real_world_cases = [
        case for case in first["cases"]
        if case["source"].startswith("fixtures/benchmark/")
    ]
    assert first["real_world_case_count"] == len(real_world_cases)
    assert first["real_world_case_count"] >= 1


def test_converter_parity_report_hashes_both_outputs():
    report_module = _load_report_module()
    report = report_module.collect_report()

    for case in report["cases"]:
        assert len(case["legacy_sha256"]) == 64
        assert len(case["dom_sha256"]) == 64
        if case["equal"]:
            assert case["legacy_sha256"] == case["dom_sha256"]
        else:
            assert case["legacy_sha256"] != case["dom_sha256"]


def test_converter_parity_report_does_not_force_dom_first():
    report_module = _load_report_module()
    report = report_module.collect_report()

    if report["mismatch_count"]:
        expected = "investigate_mismatches_before_dom_first"
    elif report["real_world_case_count"] < 2:
        expected = "expand_real_world_corpus_before_dom_first"
    else:
        expected = "candidate_for_dom_first_evaluation"
    assert report["decision_hint"] == expected


def test_converter_parity_report_covers_requested_synthetic_categories():
    report_module = _load_report_module()
    expected = {
        "blockquote",
        "inline_code",
        "preformatted_code",
        "alt_only_image",
        "safe_relative_image",
    }
    assert expected <= set(report_module.SYNTHETIC_CASES)
    assert report_module.SYNTHETIC_CASES["alt_only_image"] == '<img alt="description">'
    assert (
        report_module.SYNTHETIC_CASES["safe_relative_image"]
        == '<img src="/missing.png" alt="description">'
    )


def test_converter_parity_report_flags_thin_real_world_corpus():
    report_module = _load_report_module()
    report = report_module.collect_report()

    assert "real-world html coverage" in report["corpus_note"].lower()
    if report["real_world_case_count"] < 2 and report["mismatch_count"] == 0:
        assert report["decision_hint"] == "expand_real_world_corpus_before_dom_first"


def test_tohoho_real_world_fixture_matches_dom_path():
    report_module = _load_report_module()
    report = report_module.collect_report()
    tohoho = next(case for case in report["cases"] if case["id"] == "tohoho_web_home")
    if not tohoho["equal"]:
        import markdown as md
        html = (ROOT / "fixtures" / "benchmark" / "tohoho_web_home.html").read_text(encoding="utf-8")
        legacy = md.html_to_markdown(html)
        dom = md.dom_to_markdown(md.parse_html_dom(html))
        first_diff = next(
            (i for i, (a, b) in enumerate(zip(legacy, dom)) if a != b),
            min(len(legacy), len(dom)),
        )
        lo = max(0, first_diff - 80)
        hi = first_diff + 80
        raise AssertionError(
            (
                first_diff,
                repr(legacy[lo:hi]),
                repr(dom[lo:hi]),
                len(legacy),
                len(dom),
            )
        )


# ═══ · ipynb conversion ══════════════════════════════════════════════════════════════════════════════════

def test_markdown_to_ipynb_and_back_preserves_markdown_and_python_source():
    source = "# Title\n\n```python\nvalue = 1\n```\n"
    notebook = json.loads(md.markdown_to_ipynb(source))

    assert [cell["cell_type"] for cell in notebook["cells"]] == ["markdown", "code"]
    assert notebook["cells"][1]["outputs"] == []
    assert md.ipynb_to_markdown(notebook) == source


def test_ipynb_to_markdown_rejects_non_notebook_data():
    try:
        md.ipynb_to_markdown("{}")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_markdown_to_ipynb_does_not_extract_python_fence_inside_code_context():
    source = "```md\n```python\nx = 1\n```\n```\n"
    notebook = json.loads(md.markdown_to_ipynb(source))

    assert [cell["cell_type"] for cell in notebook["cells"]] == ["markdown"]


def test_markdown_to_ipynb_uses_the_first_fence_info_token_as_language():
    source = "```python hl_lines=\"1\"\nx = 1\n```\n"
    notebook = json.loads(md.markdown_to_ipynb(source))

    assert [cell["cell_type"] for cell in notebook["cells"]] == ["code"]
    assert notebook["cells"][0]["source"] == ["x = 1\n"]


# ═══ · py percent conversion ═════════════════════════════════════════════════════════════════════════════

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


# ═══ · structured adapters ═══════════════════════════════════════════════════════════════════════════════

def test_ini_semantic_round_trip_and_canonical_fixed_point():
    source = (
        "# source comment is intentionally lossy\n"
        "[DEFAULT]\n"
        "MixedCase = 100% literal\n"
        "\n"
        "[server]\n"
        "host: localhost\n"
        "message = 日本語\n"
        "multiline = first\n"
        "    second\n"
    )

    document = md.ini_to_markdown(source)
    canonical = md.markdown_to_ini(document)

    assert md.ini_to_markdown(canonical) == document
    assert md.markdown_to_ini(md.ini_to_markdown(canonical)) == canonical
    assert "[DEFAULT]" in canonical
    assert "MixedCase=100% literal" in canonical


def test_ini_rejects_non_string_structured_values():
    document = md.structured_to_markdown({"section": {"port": 8080}})
    with pytest.raises(ValueError, match="values must be strings"):
        md.markdown_to_ini(document)


def test_dotenv_semantic_round_trip_and_canonical_fixed_point():
    source = (
        "# ignored comment\n"
        "export NAME=妙本\n"
        "EMPTY=\n"
        "PIPE=\"a|b\"\n"
        "MULTILINE=\"line\\nbreak\"\n"
        "LITERAL_DOLLAR=$HOME\n"
    )

    document = md.dotenv_to_markdown(source)
    canonical = md.markdown_to_dotenv(document)

    assert md.dotenv_to_markdown(canonical) == document
    assert md.markdown_to_dotenv(md.dotenv_to_markdown(canonical)) == canonical
    assert 'NAME="妙本"' in canonical
    assert 'LITERAL_DOLLAR="$HOME"' in canonical


def test_dotenv_rejects_duplicate_and_invalid_keys():
    with pytest.raises(ValueError, match="Duplicate"):
        md.dotenv_to_markdown("A=1\nA=2\n")
    with pytest.raises(ValueError, match="Invalid dotenv"):
        md.dotenv_to_markdown("BAD-KEY=value\n")


@pytest.mark.skipif(md.toml_reader() is None, reason="needs tomllib (3.11+) or Node with smol-toml")
def test_toml_semantic_round_trip_and_canonical_fixed_point():
    source = (
        'title = "TOML Example"\n'
        'enabled = true\n'
        'ratio = 1.25\n'
        'ports = [8000, 8001]\n'
        '\n'
        '[owner]\n'
        'name = "妙本"\n'
        '\n'
        '[database]\n'
        'data = [["delta", "phi"], [3.14]]\n'
        '\n'
        '[[products]]\n'
        'name = "Hammer"\n'
        'sku = 738594937\n'
        '\n'
        '[[products]]\n'
        'name = "Nail"\n'
        'sku = 284758393\n'
    )

    document = md.toml_to_markdown(source)
    canonical = md.markdown_to_toml(document)

    assert md.toml_to_markdown(canonical) == document
    assert md.markdown_to_toml(md.toml_to_markdown(canonical)) == canonical


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is Python 3.11+")
def test_toml_quoted_keys_and_nested_values_round_trip():
    source = (
        '"a.b" = { "sp ace" = "x|y", nested = { flag = false } }\n'
        'unicode = "日本語"\n'
    )
    document = md.toml_to_markdown(source)
    canonical = md.markdown_to_toml(document)
    assert md.toml_to_markdown(canonical) == document


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is Python 3.11+")
def test_toml_rejects_datetime_and_non_finite_values():
    with pytest.raises(ValueError, match="outside the reversible"):
        md.toml_to_markdown("when = 2026-09-21T12:00:00Z\n")
    with pytest.raises(ValueError, match="outside the reversible"):
        md.toml_to_markdown("value = inf\n")


def test_markdown_to_toml_rejects_null():
    document = md.structured_to_markdown({"value": None})
    with pytest.raises(ValueError, match="no null"):
        md.markdown_to_toml(document)


def test_toml_reader_requires_python_311_when_tomllib_unavailable(monkeypatch):
    monkeypatch.setattr(md, "tomllib", None)
    monkeypatch.setattr(md, "_TOML_READER", [None])  # and no Node fallback
    with pytest.raises(RuntimeError, match=r"3\.11.*Node 26\+"):
        md.toml_to_markdown('x = 1\n')


@pytest.mark.parametrize(
    "value",
    [
        {"bad\nsection": {"key": "value"}},
        {"bad\rsection": {"key": "value"}},
        {"section": {"bad\nkey": "value"}},
        {"section": {"bad\rkey": "value"}},
    ],
)
def test_markdown_to_ini_rejects_embedded_newlines_in_names(value):
    document = md.structured_to_markdown(value)
    with pytest.raises(ValueError, match="single-line"):
        md.markdown_to_ini(document)


# ═══ · structured snapshots ══════════════════════════════════════════════════════════════════════════════

def test_json_and_redis_snapshots_are_lossless_without_connection():
    value = {"user": {"name": "妙本"}, "tags": ["ai", "md"], "ttl": 60}
    assert md.markdown_to_json(md.json_to_markdown(value)) == value
    assert md.markdown_to_json(md.redis_snapshot_to_markdown(value)) == value


def test_sql_snapshot_preserves_multiline_values_and_trailing_newlines():
    ddl = "CREATE TABLE logs (\n  id int,\n  note text\n);\n\n\n"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(ddl)) == ddl


def test_sql_snapshot_lists_quoted_and_bracket_table_names():
    tick = chr(96)
    ddl = (
        'CREATE TABLE "my table" (id int);\n'
        + "CREATE TABLE " + tick + "order items" + tick + " (id int);\n"
        + "CREATE TABLE [select] (id int);"
    )
    document = md.sql_ddl_to_markdown(ddl)

    assert 'Table: "my table"' in document
    assert "Table: " + tick + "order items" + tick in document
    assert "Table: [select]" in document
    assert md.markdown_to_sql_ddl(document) == ddl

def test_sql_snapshot_lists_qualified_and_escaped_quoted_names():
    ddl = 'CREATE TABLE "schema"."my table" (id int);\nCREATE TABLE "my ""table""" (id int);'
    document = md.sql_ddl_to_markdown(ddl)

    assert 'Table: "schema"."my table"' in document
    assert 'Table: "my ""table"""' in document
    assert md.markdown_to_sql_ddl(document) == ddl


def test_markdown_table_statistics_reports_only_fully_numeric_columns():
    source = "| name | score |\n| --- | --- |\n| a | 1 |\n| b | 3 |\n"

    assert md.markdown_table_statistics(source) == {
        "rows": 2,
        "columns": 2,
        "headers": ["name", "score"],
        "numeric_columns": {
            "score": {"count": 2, "min": 1.0, "max": 3.0, "mean": 2.0, "median": 2.0}
        },
    }


def test_markdown_table_statistics_excludes_nan_and_inf_spellings():
    """float() happily parses "nan"/"inf"/"infinity" -- a text column
    using those words is not numeric data and must not be aggregated."""
    source = "| name | flag |\n| --- | --- |\n| a | nan |\n| b | NaN |\n"
    assert md.markdown_table_statistics(source)["numeric_columns"] == {}

    inf_source = "| name | score |\n| --- | --- |\n| a | 1 |\n| b | inf |\n"
    assert md.markdown_table_statistics(inf_source)["numeric_columns"] == {}


def test_markdown_table_statistics_rejects_duplicate_headers():
    """numeric_columns is keyed by header text, which can't represent two
    columns of the same name losslessly -- same contract as
    markdown_table_to_records, which also raises on duplicate headers."""
    source = "| score | score |\n| --- | --- |\n| 1 | 100 |\n| 3 | 200 |\n"
    with pytest.raises(ValueError, match="unique"):
        md.markdown_table_statistics(source)


def test_sql_snapshot_normalizes_crlf_to_lf():
    ddl = "CREATE TABLE t (id int);\r\n"
    document = md.sql_ddl_to_markdown(ddl)

    assert "\r" not in document
    assert md.markdown_to_sql_ddl(document) == "CREATE TABLE t (id int);\n"


def test_sql_snapshot_preserves_normalized_trailing_newline_count():
    ddl = "CREATE TABLE t (id int);\r\n\r\n"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(ddl)) == (
        "CREATE TABLE t (id int);\n\n"
    )


def test_sql_snapshot_normalizes_lone_cr_to_lf():
    ddl = "CREATE TABLE t (id int);\rCREATE TABLE u (id int);\r"
    assert md.markdown_to_sql_ddl(md.sql_ddl_to_markdown(ddl)) == (
        "CREATE TABLE t (id int);\nCREATE TABLE u (id int);\n"
    )


def test_structured_markdown_round_trip_nested_json_compatible_values():
    value = {
        "user": {"name": "妙本", "active": True, "score": 1.5},
        "tags": ["ai", "a|b", "line\nbreak"],
        "empty_map": {},
        "empty_list": [],
        "none": None,
        "count": 3,
    }

    document = md.structured_to_markdown(value)

    assert "<!-- markdown.py:structured-v1 -->" in document
    assert md.markdown_to_structured(document) == value


def test_structured_markdown_round_trip_root_scalars_and_containers():
    for value in [None, True, 0, -3, 1.25, "日本語|\\n", [], {}]:
        assert md.markdown_to_structured(md.structured_to_markdown(value)) == value


def test_structured_markdown_rejects_non_string_mapping_keys():
    with pytest.raises(TypeError, match="string keys"):
        md.structured_to_markdown({1: "value"})


def test_structured_markdown_rejects_non_finite_float():
    with pytest.raises(ValueError):
        md.structured_to_markdown(float("nan"))


def test_markdown_to_structured_rejects_noncanonical_headers():
    source = (
        "<!-- markdown.py:structured-v1 -->\n"
        "| key | value |\n"
        "| --- | --- |\n"
        "| a | 1 |\n"
    )
    with pytest.raises(ValueError, match="canonical"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_type_mismatch():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | int | \"text\" |\n"
    )
    with pytest.raises(ValueError, match="type mismatch"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_bad_parent_reference():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
        "| 1 | 9 | \"x\" | int | 1 |\n"
    )
    with pytest.raises(ValueError, match="earlier node"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_requires_format_marker():
    source = (
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
    )
    with pytest.raises(ValueError, match="marker"):
        md.markdown_to_structured(source)


def test_structured_markdown_round_trip_tricky_keys_and_values():
    value = {
        "a|b": "pipe|value",
        "quote\"key": "backslash\\value",
        "日本語": ["改行\n入り", "", False],
    }
    assert md.markdown_to_structured(md.structured_to_markdown(value)) == value


def test_structured_markdown_rejects_tuple_and_bytes():
    with pytest.raises(TypeError):
        md.structured_to_markdown(("a", "b"))
    with pytest.raises(TypeError):
        md.structured_to_markdown(b"bytes")


def test_structured_markdown_rejects_positive_and_negative_infinity():
    for value in [float("inf"), float("-inf")]:
        with pytest.raises(ValueError):
            md.structured_to_markdown(value)


def test_markdown_to_structured_rejects_duplicate_mapping_key():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
        "| 1 | 0 | \"x\" | int | 1 |\n"
        "| 2 | 0 | \"x\" | int | 2 |\n"
    )
    with pytest.raises(ValueError, match="duplicate key"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_out_of_order_list_slot():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | list |  |\n"
        "| 1 | 0 | 1 | int | 1 |\n"
    )
    with pytest.raises(ValueError, match="contiguous"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_unknown_type_tag():
    source = (
        "# Structured data\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | datetime | \"2026-09-21T00:00:00\" |\n"
    )
    with pytest.raises(ValueError, match="Unknown structured node type"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_marker_only_as_substring():
    source = (
        "prose <!-- markdown.py:structured-v1 --> prose\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
    )
    with pytest.raises(ValueError, match="marker"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_rejects_marker_in_fenced_example():
    source = (
        "```markdown\n"
        "<!-- markdown.py:structured-v1 -->\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
        "```\n"
    )
    with pytest.raises(ValueError, match="marker"):
        md.markdown_to_structured(source)


def test_markdown_to_structured_requires_table_paired_with_marker():
    source = (
        "<!-- markdown.py:structured-v1 -->\n"
        "intervening prose\n"
        "| id | parent | slot | type | value |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 0 |  |  | dict |  |\n"
    )
    with pytest.raises(ValueError, match="paired"):
        md.markdown_to_structured(source)


# ═══ · system formats ════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_exports() -> None:
    for name in (
        "calendar_to_markdown",
        "platform_to_markdown",
        "email_to_markdown",
        "markdown_to_email",
        "markdown_to_man",
    ):
        assert name in md.__all__


# --- calendar ---------------------------------------------------------------

def test_calendar_month_table_is_deterministic_english() -> None:
    out = md.calendar_to_markdown(2026, 9)
    assert out.startswith("## September 2026\n\n| Mon | Tue | Wed | Thu | Fri | Sat | Sun |\n")
    assert "|  | 1 | 2 | 3 | 4 | 5 | 6 |" in out
    assert "| 28 | 29 | 30 |  |  |  |  |" in out
    rows = md.markdown_table_to_rows(out)[1]
    days = [cell for row in rows for cell in row if cell]
    assert days == [str(day) for day in range(1, 31)]


def test_calendar_first_weekday_and_title() -> None:
    out = md.calendar_to_markdown(2026, 2, firstweekday=6, title="Feb")
    assert out.startswith("## Feb\n\n| Sun | Mon |")
    assert "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |" in out


@pytest.mark.parametrize("kwargs", [{"month": 13}, {"month": 0}, {"month": 1, "firstweekday": 7}])
def test_calendar_rejects_out_of_range(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        md.calendar_to_markdown(2026, **kwargs)


# --- platform ---------------------------------------------------------------

def test_platform_table_has_expected_keys_and_no_host_identity() -> None:
    import platform

    out = md.platform_to_markdown()
    headers, rows = md.markdown_table_to_rows(out)
    assert headers == ["Key", "Value"]
    keys = [row[0] for row in rows]
    assert keys[:3] == ["Python", "Implementation", "Compiler"]
    assert dict(rows)["Python"] == platform.python_version()
    node = platform.node()
    if node:
        assert node not in out


# --- email ------------------------------------------------------------------

SAMPLE_MD = "# Hi\n\nSee **this** and `code`.\n\n- a\n- b\n"


def _build(**overrides: object) -> str:
    kwargs: dict = {
        "subject": "Report 日本語",
        "sender": "a@example.com",
        "to": ["b@example.com", "c@example.com"],
        "date": datetime.datetime(2026, 9, 26, 12, 0, tzinfo=datetime.timezone.utc),
    }
    kwargs.update(overrides)
    return md.markdown_to_email(SAMPLE_MD, **kwargs)


def test_markdown_to_email_is_multipart_alternative() -> None:
    import email
    from email import policy

    message = email.message_from_string(_build(), policy=policy.default)
    assert message.get_content_type() == "multipart/alternative"
    assert message["To"] == "b@example.com, c@example.com"
    assert message.get_body(("plain",)).get_content() == SAMPLE_MD
    html = message.get_body(("html",)).get_content()
    assert "<strong>this</strong>" in html


def test_email_round_trip_recovers_markdown_body_and_headers() -> None:
    out = md.email_to_markdown(_build())
    assert out.startswith("# Report 日本語\n")
    assert "| From | a@example.com |" in out
    assert "| Date | Sat, 26 Sep 2026 12:00:00 +0000 |" in out
    assert SAMPLE_MD.strip("\n") in out


def test_markdown_to_email_omits_date_when_not_given() -> None:
    assert "Date:" not in _build(date=None)


def test_markdown_to_email_rejects_header_injection() -> None:
    with pytest.raises(ValueError):
        _build(subject="hi\nBcc: victim@example.com")


def test_email_html_only_body_goes_through_html_to_markdown() -> None:
    raw = (
        "From: a@example.com\n"
        "Subject: html\n"
        "Content-Type: text/html; charset=utf-8\n"
        "\n"
        "<p>Hello <b>World</b></p><script>alert(1)</script>\n"
    )
    out = md.email_to_markdown(raw)
    assert "**World**" in out
    assert "<script>" not in out


def test_email_attachments_are_listed_not_decoded_to_disk(tmp_path: Path) -> None:
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = "files"
    msg["From"] = "a@example.com"
    msg.set_content("body text\n")
    msg.add_attachment(b"\x00\x01\x02", maintype="application", subtype="octet-stream", filename="blob.bin")
    out = md.email_to_markdown(msg.as_bytes())
    assert "## Attachments" in out
    assert "| blob.bin | application/octet-stream | 3 |" in out
    assert "body text" in out
    assert list(tmp_path.iterdir()) == []


def test_email_unknown_charset_falls_back_to_replacement_decoding() -> None:
    raw = "From: a@example.com\nSubject: s\nContent-Type: text/plain; charset=x-unknown\n\nhello\n"
    assert md.email_to_markdown(raw).endswith("\nhello\n")


def test_email_without_subject() -> None:
    assert md.email_to_markdown("From: a@example.com\n\nbody\n").startswith("# (no subject)\n")


# --- man --------------------------------------------------------------------

MAN_SOURCE = (
    "# Name\n\n"
    "mytool - does things\n\n"
    "## Options\n\n"
    "- `--verbose` : be **loud**\n"
    "- `-q` quiet\n\n"
    ".dangerous line\n"
    "'also dangerous\n\n"
    "```sh\n"
    "mytool --help\n"
    ".also-code\n"
    "```\n\n"
    "> quoted *text*\n\n"
    "See [docs](https://example.com) and <https://x.y>.\n"
)


def test_markdown_to_man_structure() -> None:
    out = md.markdown_to_man(MAN_SOURCE, name="mytool", date="2026-09-26")
    lines = out.splitlines()
    assert lines[0] == '.TH "MYTOOL" "1" "2026\\-09\\-26" "" ""'
    assert ".SH NAME" in lines
    assert ".SS Options" in lines
    assert "mytool \\- does things" in lines
    assert "\\fB\\-\\-verbose\\fR : be \\fBloud\\fR" in lines
    assert lines.count(".IP \\(bu 4") == 2
    assert ".EX" in lines and ".EE" in lines
    assert "quoted \\fItext\\fR" in lines
    assert "See docs <https://example.com> and https://x.y." in lines


def test_markdown_to_man_never_emits_injected_requests() -> None:
    out = md.markdown_to_man(MAN_SOURCE, name="mytool")
    known = (".TH", ".SH", ".SS", ".PP", ".IP", ".EX", ".EE", ".RS", ".RE")
    for line in out.splitlines():
        if line.startswith((".", "'")):
            assert line.startswith(known), line
    assert "\\&.dangerous line" in out
    assert "\\&'also dangerous" in out
    assert "\\&.also\\-code" in out


def test_markdown_to_man_escapes_backslashes_and_nested_lists() -> None:
    out = md.markdown_to_man("C:\\path\n\n1. one\n   - nested\n", name="x")
    assert "C:\\epath" in out
    assert ".IP 1. 4" in out
    assert ".IP \\(bu 6" in out


@pytest.mark.parametrize("field", ["name", "section", "date", "source", "manual"])
@pytest.mark.parametrize("bad", ["x\n.so /etc/passwd", "x\r.sh", "x\x00"])
def test_markdown_to_man_rejects_control_characters_in_th_fields(field: str, bad: str) -> None:
    kwargs = {"name": "tool", field: bad}
    with pytest.raises(ValueError, match=field):
        md.markdown_to_man("# NAME\n", **kwargs)


# ═══ · table data conversion ═════════════════════════════════════════════════════════════════════════════
# P2 table data conversions and CJK display-width contracts.

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_csv_table_csv_round_trip_handles_quotes_and_pipes() -> None:
    source = 'name,note\n妙本,"a, b | c"\n'
    table = md.csv_to_markdown_table(source)

    assert "妙本" in table
    assert "a, b \\| c" in table
    assert md.markdown_table_to_csv(table) == source


def test_csv_table_csv_round_trip_preserves_backslashes() -> None:
    source = 'path,note\n"C:\\work\\demo","literal \\| pipe"\n'
    result = md.markdown_table_to_csv(md.csv_to_markdown_table(source))
    assert list(csv.reader(io.StringIO(result))) == list(csv.reader(io.StringIO(source)))


def test_aligned_table_uses_cjk_display_width() -> None:
    table = md.aligned_table(["項目", "value"], [["猫", "1"], ["wide", "二"]])
    lines = table.splitlines()

    assert lines[0] == "| 項目 | value |"
    assert lines[2] == "| 猫   | 1     |"
    assert lines[3] == "| wide | 二    |"


def test_table_to_rows_ignores_fenced_examples_and_pads_short_rows() -> None:
    source = "```markdown\n| ignored | table |\n| --- | --- |\n| x | y |\n```\n| a | b |\n| --- | --- |\n| 1 |\n"
    assert md.markdown_table_to_rows(source) == (["a", "b"], [["1", ""]])


def test_table_to_records_rejects_duplicate_headers() -> None:
    source = "| a | a |\n| --- | --- |\n| 1 | 2 |\n"
    with pytest.raises(ValueError, match="unique"):
        md.markdown_table_to_records(source)


def test_malformed_or_missing_table_degrades_to_empty_data() -> None:
    assert md.markdown_table_to_rows("| a | b |\n| nope |\n") == ([], [])
    assert md.csv_to_markdown_table("") == ""


# ═══ · llm io ════════════════════════════════════════════════════════════════════════════════════════════

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_exports_llm_io() -> None:
    for name in (
        "split_reasoning",
        "compact_llm_output",
        "llm_output_digest",
        "extract_identifiers",
    ):
        assert name in md.__all__


# --- split_reasoning ---------------------------------------------------------


@pytest.mark.parametrize("tag", ["think", "thinking", "reasoning"])
def test_split_reasoning_recognizes_each_tag_format(tag: str) -> None:
    result = md.split_reasoning(f"<{tag}>pondering</{tag}>The answer.\n")
    assert result == {
        "answer": "The answer.\n",
        "reasoning": ["pondering"],
        "formats": [tag],
    }


def test_split_reasoning_is_case_insensitive_and_tolerates_attributes() -> None:
    result = md.split_reasoning('<THINK class="x">hello</THINK>ans')
    assert result == {"answer": "ans\n", "reasoning": ["hello"], "formats": ["think"]}


def test_split_reasoning_openwebui_details_drops_summary_line() -> None:
    text = (
        '<details type="reasoning" done="true" duration="12">\n'
        "<summary>Thought for 12 seconds</summary>\n"
        "Let me work through this step by step.\n"
        "The answer is 42.\n"
        "</details>\n"
        "\n"
        "The answer is 42.\n"
    )
    result = md.split_reasoning(text)
    assert result["formats"] == ["details"]
    assert result["reasoning"] == ["Let me work through this step by step.\nThe answer is 42."]
    assert "Thought for 12 seconds" not in result["reasoning"][0]
    assert result["answer"] == "The answer is 42.\n"


def test_split_reasoning_ignores_tags_in_fenced_code() -> None:
    text = "Use `<think>` in prompts.\n\n```\n<think>fake</think>\n```\n\nReal answer.\n"
    result = md.split_reasoning(text)
    assert result == {"answer": text, "reasoning": [], "formats": []}


def test_split_reasoning_ignores_tags_in_inline_code() -> None:
    text = "before `<reasoning>x</reasoning>` after\n"
    result = md.split_reasoning(text)
    assert result == {"answer": text, "reasoning": [], "formats": []}


def test_split_reasoning_plain_details_without_reasoning_type_is_not_reasoning() -> None:
    text = "<details><summary>Click me</summary>body</details>ans"
    result = md.split_reasoning(text)
    assert result == {"answer": text + "\n", "reasoning": [], "formats": []}


def test_split_reasoning_unclosed_tag_makes_the_rest_reasoning() -> None:
    result = md.split_reasoning("Before.\n<think>\nI was thinking and then the stream")
    assert result == {
        "answer": "Before.\n",
        "reasoning": ["I was thinking and then the stream"],
        "formats": ["think"],
    }


def test_split_reasoning_unclosed_openwebui_details() -> None:
    text = '<details type="reasoning">\n<summary>Thinking</summary>\ncut off mid'
    result = md.split_reasoning(text)
    assert result["formats"] == ["details"]
    assert result["answer"] == ""
    assert "cut off mid" in result["reasoning"][0]


def test_split_reasoning_multiple_blocks_in_order() -> None:
    result = md.split_reasoning("<think>one</think>Body<reasoning>two</reasoning> end")
    assert result["reasoning"] == ["one", "two"]
    assert result["formats"] == ["think", "reasoning"]
    assert result["answer"] == "Body end\n"


def test_split_reasoning_collapses_blank_runs_left_behind() -> None:
    result = md.split_reasoning("Before\n<think>\nreasoning\n</think>\n\nAfter\n")
    assert result["answer"] == "Before\n\nAfter\n"


def test_split_reasoning_pure_reasoning_leaves_empty_answer() -> None:
    result = md.split_reasoning("<think>only reasoning, no answer</think>")
    assert result["answer"] == ""
    assert result["reasoning"] == ["only reasoning, no answer"]


def test_split_reasoning_empty_input() -> None:
    assert md.split_reasoning("") == {"answer": "", "reasoning": [], "formats": []}


def test_split_reasoning_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.split_reasoning(123)  # type: ignore[arg-type]


# --- compact_llm_output -------------------------------------------------------


def test_compact_llm_output_drops_reasoning_by_default() -> None:
    text = "<think>long private reasoning</think>Line1\n\n\n\nLine2\n"
    assert md.compact_llm_output(text) == "Line1\n\nLine2\n"


def test_compact_llm_output_keep_reasoning_true_keeps_tags() -> None:
    text = "<think>long private reasoning</think>Line1\n\n\n\nLine2\n"
    out = md.compact_llm_output(text, keep_reasoning=True)
    assert "<think>long private reasoning</think>" in out
    assert out == "<think>long private reasoning</think>Line1\n\nLine2\n"


def test_compact_llm_output_max_blank_lines_is_configurable() -> None:
    text = "Line1\n\n\n\nLine2\n"
    assert md.compact_llm_output(text, max_blank_lines=0) == "Line1\nLine2\n"
    assert md.compact_llm_output(text, max_blank_lines=2) == "Line1\n\n\nLine2\n"


def test_compact_llm_output_short_code_block_is_untouched() -> None:
    code = "\n".join(f"line{i}" for i in range(1, 41))
    text = f"```python\n{code}\n```\n"
    assert md.compact_llm_output(text, max_code_lines=40) == text


def test_compact_llm_output_truncates_long_code_block_with_marker() -> None:
    code = "\n".join(f"line{i}" for i in range(1, 51))
    text = f"```python\n{code}\n```\n"
    out = md.compact_llm_output(text, max_code_lines=5)
    lines = out.splitlines()
    assert lines[:7] == ["```python", "line1", "line2", "line3", "line4", "line5", "… 45 more lines"]
    assert lines[-1] == "```"
    # Never alter kept code content.
    for i in range(1, 6):
        assert f"line{i}" in out
    assert "line50" not in out


def test_compact_llm_output_truncation_keeps_fence_stable_with_backtick_runs() -> None:
    # The outer fence must already be 4 backticks for an inner ``` line to be
    # legitimate content; this is exactly what the adaptive fence protects.
    inner = ["line1", "```", "line3"] + [f"line{i}" for i in range(4, 51)]
    text = "````python\n" + "\n".join(inner) + "\n````\n"
    out = md.compact_llm_output(text, max_code_lines=5)
    blocks = md.extract_code_blocks(out)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"
    assert blocks[0]["code"].splitlines()[:6] == ["line1", "```", "line3", "line4", "line5", "… 45 more lines"]
    # The re-fence must be longer than the ``` run now inside the body.
    assert out.count("````") == 2


def test_compact_llm_output_truncation_preserves_tilde_fence() -> None:
    # A ~~~-fenced block must stay ~~~-fenced after truncation, not switch to
    # backtick (code_block()'s default), and its own adaptive fence still
    # grows past a ~~~ run left inside the kept body.
    text = "~~~python\n" + "\n".join(f"line{i}" for i in range(1, 51)) + "\n~~~\n"
    out = md.compact_llm_output(text, max_code_lines=5)
    assert out.startswith("~~~python\n")
    assert "```" not in out

    inner = ["a", "~~~", "b"] + [f"line{i}" for i in range(4, 51)]
    text_with_run = "~~~~python\n" + "\n".join(inner) + "\n~~~~\n"
    out_with_run = md.compact_llm_output(text_with_run, max_code_lines=5)
    assert out_with_run.count("~~~~") == 2


def test_compact_llm_output_empty_input() -> None:
    assert md.compact_llm_output("") == ""


@pytest.mark.parametrize(
    "kwargs",
    [{"max_code_lines": -1}, {"max_blank_lines": -1}],
)
def test_compact_llm_output_rejects_negative_params(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        md.compact_llm_output("hello", **kwargs)


def test_compact_llm_output_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.compact_llm_output(None)  # type: ignore[arg-type]


# --- llm_output_digest ---------------------------------------------------------


def test_llm_output_digest_fields() -> None:
    text = (
        "<think>secret</think>"
        "# Title\n\n"
        "Some answer [link](https://example.com).\n\n"
        "```python\nprint(1)\n```\n"
    )
    digest = md.llm_output_digest(text)
    assert digest["reasoning_blocks"] == 1
    assert digest["reasoning_chars"] == len("secret")
    assert digest["headings"] == ["Title"]
    assert digest["code_blocks"] == [{"lang": "python", "lines": 1}]
    assert digest["links"] == ["https://example.com"]
    assert digest["has_table"] is False
    assert digest["answer_chars"] == len(md.split_reasoning(text)["answer"])


def test_llm_output_digest_has_table() -> None:
    with_table = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    assert md.llm_output_digest(with_table)["has_table"] is True
    assert md.llm_output_digest("no table here\n")["has_table"] is False


def test_llm_output_digest_multiple_reasoning_blocks() -> None:
    digest = md.llm_output_digest("<think>one</think>Body<reasoning>two</reasoning> end")
    assert digest["reasoning_blocks"] == 2
    assert digest["reasoning_chars"] == len("one") + len("two")


def test_llm_output_digest_empty_input() -> None:
    assert md.llm_output_digest("") == {
        "answer_chars": 0,
        "reasoning_chars": 0,
        "reasoning_blocks": 0,
        "headings": [],
        "code_blocks": [],
        "links": [],
        "has_table": False,
    }


def test_llm_output_digest_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.llm_output_digest(123)  # type: ignore[arg-type]


# --- extract_identifiers -------------------------------------------------------


def test_extract_identifiers_finds_each_category() -> None:
    text = (
        "See 550e8400-e29b-41d4-a716-446655440000 and "
        "https://example.com/path plus deadbeef123 alone. "
        "Also myon-bioinformatics/markdown#61 and bare #7.\n"
    )
    ids = md.extract_identifiers(text)
    assert ids["uuids"] == ["550e8400-e29b-41d4-a716-446655440000"]
    assert ids["urls"] == ["https://example.com/path"]
    assert ids["github_refs"] == ["myon-bioinformatics/markdown#61", "#7"]
    assert ids["shas"] == ["deadbeef123"]


def test_extract_identifiers_uuid_is_not_split_into_shas() -> None:
    ids = md.extract_identifiers("id 550e8400-e29b-41d4-a716-446655440000 here\n")
    assert ids["shas"] == []
    assert ids["uuids"] == ["550e8400-e29b-41d4-a716-446655440000"]


def test_extract_identifiers_urls_hex_is_not_counted_as_a_sha() -> None:
    ids = md.extract_identifiers("see https://x.com/commit/abcdef1234567 now\n")
    assert ids["shas"] == []
    assert ids["urls"] == ["https://x.com/commit/abcdef1234567"]


def test_extract_identifiers_pure_digit_or_pure_letter_runs_are_not_shas() -> None:
    ids = md.extract_identifiers("call 1234567 and deadbeef please\n")
    assert ids["shas"] == []


def test_extract_identifiers_skips_fenced_code_but_not_inline_code() -> None:
    text = (
        "inline `deadbeef123` stays\n\n"
        "```\n"
        "ffffffff9 550e8400-e29b-41d4-a716-446655440000\n"
        "```\n"
    )
    ids = md.extract_identifiers(text)
    assert ids["shas"] == ["deadbeef123"]
    assert ids["uuids"] == []


def test_extract_identifiers_skips_urls_and_github_refs_in_fenced_code_too() -> None:
    text = (
        "real https://example.com/x and myon/repo#9 here.\n\n"
        "```\n"
        "https://fenced.example.com/y and other/thing#3\n"
        "```\n"
    )
    ids = md.extract_identifiers(text)
    assert ids["urls"] == ["https://example.com/x"]
    assert ids["github_refs"] == ["myon/repo#9"]


def test_extract_identifiers_dedupes_in_order_of_appearance() -> None:
    text = "dup #5 stuff #5 again, then #9, then #5 once more\n"
    ids = md.extract_identifiers(text)
    assert ids["github_refs"] == ["#5", "#9"]


def test_extract_identifiers_empty_input() -> None:
    assert md.extract_identifiers("") == {
        "uuids": [],
        "urls": [],
        "github_refs": [],
        "shas": [],
    }


def test_extract_identifiers_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        md.extract_identifiers(123)  # type: ignore[arg-type]


def test_extract_identifiers_hex_runs_need_word_boundaries() -> None:
    assert md.extract_identifiers("see Name1234567 and x_abc1234")["shas"] == []
    assert md.extract_identifiers("fixed in abc1234.")["shas"] == ["abc1234"]


# ═══ · reference generators ══════════════════════════════════════════════════════════════════════════════

def test_inspect_to_markdown_function_reference_is_deterministic():
    def sample(value, flag=False):
        """Return a sample value.

        Longer documentation stays in the description section.
        """
        return str(value)

    first = md.inspect_to_markdown(sample, title="Sample API")
    second = md.inspect_to_markdown(sample, title="Sample API")

    assert first == second
    assert first.startswith("# Sample API\n")
    assert "| Kind | function |" in first
    assert "## Description" in first
    assert "Return a sample value." in first
    assert "(value, flag=False)" in first


def test_inspect_to_markdown_class_does_not_invoke_properties():
    class Safe:
        """Safe API."""

        @property
        def dangerous(self):
            raise AssertionError("property must not be invoked")

        def run(self, value):
            """Run one value."""
            return value

        @staticmethod
        def helper(item):
            """Help with an item."""
            return item

    result = md.inspect_to_markdown(Safe)

    assert "dangerous" not in result
    assert "| run | function | (self, value) | Run one value. |" in result
    assert "| helper | function | (item) | Help with an item. |" in result


def test_inspect_to_markdown_module_lists_only_owned_public_api():
    module = types.ModuleType("demo_module")

    def owned(value):
        """Owned function."""
        return value

    def imported(value):
        return value

    owned.__module__ = "demo_module"
    imported.__module__ = "other_module"
    module.owned = owned
    module.imported = imported
    module._private = owned

    result = md.inspect_to_markdown(module)

    assert "| owned | function | (value) | Owned function. |" in result
    assert "imported" not in result
    assert "_private" not in result


def test_argparse_to_markdown_documents_arguments_and_subcommands():
    parser = argparse.ArgumentParser(
        prog="demo",
        description="Demo CLI.",
        epilog="Done.",
    )
    parser.add_argument("path", help="Input path")
    parser.add_argument("--mode", choices=["fast", "safe"], default="safe", help="Run mode")
    parser.add_argument("--count", type=int, metavar="N", required=True, help="Count")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    subs = parser.add_subparsers(dest="command")
    child = subs.add_parser("serve", description="Serve content")
    child.add_argument("--port", type=int, default=8000)

    result = md.argparse_to_markdown(parser)

    assert result.startswith("# CLI: demo\n")
    assert "## Usage" in result
    assert "| path | yes |" in result
    assert "| --mode | no |  | fast, safe | safe |  |  | store | Run mode |" in result
    assert "| --count | yes |  |  |  | int | N | store | Count |" in result
    assert "| --verbose | no | 0 |  | False |  |  | store_true | Verbose output |" in result
    assert "## Subcommands" in result
    assert "| serve | Serve content |" in result
    assert "## Epilog" in result
    assert result == md.argparse_to_markdown(parser)


def test_argparse_to_markdown_rejects_non_parser():
    with pytest.raises(TypeError, match="ArgumentParser"):
        md.argparse_to_markdown(object())


class _FakeMetadata(dict):
    def get_all(self, key):
        if key == "Project-URL":
            return ["Docs, https://example.test/docs", "Source, https://example.test/src"]
        return None


class _FakeEntryPoint:
    def __init__(self, group, name, value):
        self.group = group
        self.name = name
        self.value = value


class _FakeDistribution:
    version = "1.2.3"
    requires = ["zeta>=1", "alpha"]

    def __init__(self):
        self.metadata = _FakeMetadata(
            {
                "Name": "demo-package",
                "Summary": "Demo package.",
                "Requires-Python": ">=3.9",
            }
        )
        self.entry_points = [
            _FakeEntryPoint("console_scripts", "zeta", "demo:zeta"),
            _FakeEntryPoint("console_scripts", "alpha", "demo:alpha"),
        ]


def test_distribution_to_markdown_is_deterministic_and_sorted(monkeypatch):
    monkeypatch.setattr(
        md.importlib_metadata,
        "distribution",
        lambda name: _FakeDistribution(),
    )

    result = md.distribution_to_markdown("demo-package")

    assert result.startswith("# Package: demo-package\n")
    assert "| Version | 1.2.3 |" in result
    assert "## Project URLs" in result
    assert result.index("Docs") < result.index("Source")
    assert "## Requires" in result
    assert result.index("- alpha") < result.index("- zeta>=1")
    assert "## Entry Points" in result
    assert result.index("| console_scripts | alpha |") < result.index("| console_scripts | zeta |")
    assert result == md.distribution_to_markdown("demo-package")


def test_distribution_to_markdown_missing_distribution(monkeypatch):
    def missing(name):
        raise md.importlib_metadata.PackageNotFoundError(name)

    monkeypatch.setattr(md.importlib_metadata, "distribution", missing)

    with pytest.raises(ValueError, match="Distribution not found"):
        md.distribution_to_markdown("missing-package")


def test_distribution_to_markdown_rejects_empty_name():
    with pytest.raises(ValueError, match="non-empty"):
        md.distribution_to_markdown("   ")


def test_argparse_boolean_optional_action_name():
    parser = argparse.ArgumentParser(prog="demo")
    parser.add_argument(
        "--feature",
        action=argparse.BooleanOptionalAction,
        help="Toggle feature",
    )

    result = md.argparse_to_markdown(parser)

    assert "| --feature, --no-feature | no | 0 |  |  |  |  | boolean_optional | Toggle feature |" in result
