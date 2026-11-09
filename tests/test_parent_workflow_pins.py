"""Local rollout contract; adopted vendor locks are deliberately independent."""
import re
from pathlib import Path

import pytest

PARENT = "myon-bioinformatics/myon-bioinformatics"
PARENT_WORKFLOW_PIN = "9e3da7ae1846e9604ebc24bb5178f7de094a4e77"
VENDOR_TOOL_PIN = "26c442bc51b8a2837fe2556782b2937f396932af"
ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".github/workflows").is_dir())


def test_parent_workflow_references_use_reviewed_rollout_commit():
    pins = []
    vendor_tool_pins = []
    for path in sorted((ROOT / ".github/workflows").glob("*")):
        if path.suffix not in (".yml", ".yaml"):
            continue
        text = path.read_text(encoding="utf-8")
        # Capture mutable and shortened references too, rather than ignoring them.
        pins.extend(re.findall(r"uses:\s*['\"]?" + re.escape(PARENT) + r"/[^\s@'\"]+@([^\s'\"]+)", text))
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not re.fullmatch(r"\s+repository:\s*['\"]?" + re.escape(PARENT) + r"['\"]?\s*", line):
                continue
            block = lines[i + 1:i + 12]
            refs = [re.fullmatch(r"\s+ref:\s*['\"]?([^\s'\"]+)['\"]?\s*", item) for item in block]
            ref = next((m.group(1) for m in refs if m), None)
            if any(re.fullmatch(r"\s+path:\s*['\"]?\.vendor-sync-tools['\"]?\s*", item) for item in block):
                vendor_tool_pins.append(ref)
            else:
                pins.append(ref)
    assert pins, "shared parent references must remain observable"
    assert set(pins) == {PARENT_WORKFLOW_PIN}, pins
    assert vendor_tool_pins and set(vendor_tool_pins) == {VENDOR_TOOL_PIN}, vendor_tool_pins


@pytest.mark.parametrize("quote", ["", "'", '"'])
@pytest.mark.parametrize("target", ["uses", "checkout", "vendor"])
@pytest.mark.parametrize("reference", ["reviewed", "main", "9e3da7a"])
def test_reference_detection_preserves_quotes_and_rejects_unreviewed_pins(
    tmp_path, monkeypatch, quote, target, reference
):
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    # Keep valid references present so ignoring a quoted bad reference cannot pass.
    (workflows / "baseline.yml").write_text(
        f"  uses: {PARENT}/.github/workflows/ci.yml@{PARENT_WORKFLOW_PIN}\n"
        f"  repository: {PARENT}\n"
        f"  ref: {VENDOR_TOOL_PIN}\n"
        "  path: .vendor-sync-tools\n", encoding="utf-8"
    )
    pin = VENDOR_TOOL_PIN if target == "vendor" else PARENT_WORKFLOW_PIN
    ref = pin if reference == "reviewed" else reference
    if target == "uses":
        candidate = f"  uses: {quote}{PARENT}/.github/workflows/ci.yml@{ref}{quote}\n"
    else:
        path = ".vendor-sync-tools" if target == "vendor" else ".parent-workflows"
        candidate = (
            f"  repository: {quote}{PARENT}{quote}\n"
            f"  ref: {quote}{ref}{quote}\n"
            f"  path: {quote}{path}{quote}\n"
        )
    (workflows / "candidate.yml").write_text(candidate, encoding="utf-8")
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    if reference == "reviewed":
        test_parent_workflow_references_use_reviewed_rollout_commit()
    else:
        with pytest.raises(AssertionError):
            test_parent_workflow_references_use_reviewed_rollout_commit()
