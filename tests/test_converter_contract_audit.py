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

    assert report["schema_version"] == 1
    assert report["case_count"] == len(report["cases"])
    assert (
        report["case_count"]
        == report["stable_case_count"] + report["divergent_case_count"]
    )
    assert report["real_world_html_count"] >= 1
    assert report["divergent_case_ids"] == [
        case["id"] for case in report["cases"]
        if not case["all_checks_pass"]
    ]


def test_converter_contract_audit_keeps_divergence_observational():
    audit = _load_module()
    report = audit.collect_report()

    assert "not automatically a bug" in report["note"].lower()
    for case in report["cases"]:
        assert set(case["checks"])
        assert case["all_checks_pass"] == all(case["checks"].values())
