from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "converter_parity_report.py"


def _load_report_module():
    spec = importlib.util.spec_from_file_location("converter_parity_report", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_converter_parity_report_is_deterministic_and_covers_real_html():
    report_module = _load_report_module()
    first = report_module.collect_report()
    second = report_module.collect_report()

    assert first == second
    assert first["schema_version"] == 1
    assert first["case_count"] >= len(report_module.SYNTHETIC_CASES) + 1
    assert first["case_count"] == first["match_count"] + first["mismatch_count"]
    assert first["mismatch_ids"] == [
        case["id"] for case in first["cases"] if not case["equal"]
    ]
    assert any(
        case["source"].startswith("fixtures/benchmark/")
        for case in first["cases"]
    )


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

    expected = (
        "candidate_for_dom_first_evaluation"
        if report["mismatch_count"] == 0
        else "investigate_mismatches_before_dom_first"
    )
    assert report["decision_hint"] == expected
