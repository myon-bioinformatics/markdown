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
    assert tohoho["equal"] is True, (
        tohoho.get("legacy_preview"),
        tohoho.get("dom_preview"),
        tohoho.get("legacy_chars"),
        tohoho.get("dom_chars"),
    )
