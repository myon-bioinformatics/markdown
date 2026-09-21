from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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

    if audit.md.tomllib is None:
        assert ("toml", "ini") not in pairs
    else:
        assert ("toml", "ini") in pairs


def test_structured_cycles_are_stable_on_supported_python():
    audit = _load_module()
    report = audit.collect_report()
    expected_ids = {case["id"] for case in audit.STRUCTURED_CYCLE_CASES}

    if audit.md.tomllib is None:
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
